import asyncio
import io
import json
import socket
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

import app
import request_limits as limits
import url_download as download


@pytest.mark.parametrize('url', [
    'http://example.com/a.jpg', 'file:///etc/passwd', 'https://user:pass@example.com/a',
    'https://example.com:8443/a', 'https://example.com/a#fragment',
    'https://example.com\\@localhost/a', 'https://example.com/\r\nx: x',
    'https://[fe80::1%25eth0]/', 'https://example.com./a', 'https://' + 'x' * 2049,
])
def test_url_syntax_rejected(url):
    with pytest.raises(download.DownloadError) as error:
        download.validate_url(url)
    assert error.value.status == 400


@pytest.mark.parametrize('ip', ['127.0.0.1', '10.0.0.1', '172.16.0.1', '192.168.1.1',
    '169.254.169.254', '100.64.0.1', '0.0.0.0', '224.0.0.1', '::1', 'fc00::1',
    'fe80::1', '::ffff:127.0.0.1', '2002:7f00:1::', '192.0.2.1'])
def test_nonpublic_and_transition_addresses_rejected(monkeypatch, ip):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [(2, 1, 6, '', (ip, 443))])
    with pytest.raises(download.DownloadError) as error:
        download.public_address('any.example')
    assert error.value.status == 400


def test_mixed_dns_answers_rejected(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *a, **k: [
        (2, 1, 6, '', ('93.184.216.34', 443)), (2, 1, 6, '', ('10.0.0.1', 443))])
    with pytest.raises(download.DownloadError):
        download.public_address('any.example')


class Response:
    status = 200
    headers = {'Content-Type': 'image/png'}
    def __init__(self, data=b'picture'):
        self.data = io.BytesIO(data)
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size, **kwargs): return self.data.read(size)


def fake_pool(monkeypatch, response):
    observed = {}
    class Pool:
        def __init__(self, address, **kwargs): observed.update(address=address, **kwargs)
        def request(self, *args, **kwargs):
            observed['request'] = kwargs
            return response
        def close(self): observed['closed'] = True
    monkeypatch.setattr(download.urllib3, 'HTTPSConnectionPool', Pool)
    return observed


def test_dns_pinned_tls_verified_no_redirects_or_proxy(monkeypatch):
    lookups = []
    def resolve(*args, **kwargs):
        lookups.append(args)
        return [(2, 1, 6, '', ('93.184.216.34', 443))]
    monkeypatch.setattr(socket, 'getaddrinfo', resolve)
    monkeypatch.setenv('HTTPS_PROXY', 'http://127.0.0.1:1234')
    observed = fake_pool(monkeypatch, Response())
    assert download.fetch('https://images.example/cover.png') == b'picture'
    assert len(lookups) == 1
    assert observed['address'] == '93.184.216.34'
    assert observed['server_hostname'] == observed['assert_hostname'] == 'images.example'
    assert observed['cert_reqs'] == 'CERT_REQUIRED'
    assert observed['request']['headers']['Host'] == 'images.example'
    assert observed['request']['redirect'] is False
    assert observed['retries'] is False and observed['closed']


@pytest.mark.parametrize('status,headers,expected', [
    (302, {'Location': 'http://169.254.169.254/'}, 400),
    (200, {'Content-Type': 'text/html'}, 415),
    (200, {'Content-Type': 'image/png', 'Content-Encoding': 'gzip'}, 415),
    (200, {'Content-Type': 'image/png', 'Content-Length': str(download.MAX_BYTES + 1)}, 413),
    (200, {'Content-Type': 'image/png', 'Content-Length': 'broken'}, 400),
])
def test_remote_response_limits(monkeypatch, status, headers, expected):
    monkeypatch.setattr(download, 'public_address', lambda host: '93.184.216.34')
    response = Response()
    response.status, response.headers = status, headers
    fake_pool(monkeypatch, response)
    with pytest.raises(download.DownloadError) as error:
        download.fetch('https://images.example/a')
    assert error.value.status == expected


def test_stream_limit_without_content_length(monkeypatch):
    monkeypatch.setattr(download, 'public_address', lambda host: '93.184.216.34')
    monkeypatch.setattr(download, 'MAX_BYTES', 8)
    fake_pool(monkeypatch, Response(b'123456789'))
    with pytest.raises(download.DownloadError) as error:
        download.fetch('https://images.example/a')
    assert error.value.status == 413


def test_download_deadline_kills_and_reaps_child(monkeypatch, tmp_path):
    (tmp_path / 'url_download.py').write_text('import time\ntime.sleep(30)\n')
    monkeypatch.setattr(app, 'BASE_DIR', tmp_path)
    monkeypatch.setattr(app, 'DOWNLOAD_TIMEOUT_SECONDS', .2)
    real_popen = subprocess.Popen
    children = []
    def record(*args, **kwargs):
        child = real_popen(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(subprocess, 'Popen', record)
    with pytest.raises(HTTPException) as error:
        app.load_image_from_url('https://example.com/a.png')
    assert error.value.status_code == 504
    assert children and children[0].poll() is not None


@pytest.mark.parametrize('url', ['http://127.0.0.1:7860/ui/covers/HollowKnight.jpg',
    '/ui/covers/../app.py', '/ui/covers/%2e%2e/app.py', '/ui/covers/unknown.jpg'])
def test_no_local_url_or_path_escape(url):
    with TestClient(app.app) as client:
        assert client.post('/predict', json={'url': url}).status_code == 400


def test_pixel_limit_before_decoding(monkeypatch):
    class LargeImage:
        width, height, size = 4000, 4000, (4000, 4000)
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def load(self): pytest.fail('Oversized image must be rejected before decoding')
    monkeypatch.setattr(app.Image, 'open', lambda *args: LargeImage())
    with pytest.raises(HTTPException) as error:
        app.decode_image(b'header')
    assert error.value.status_code == 413


def test_animated_image_rejected():
    out = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(out, format='GIF', save_all=True,
        append_images=[Image.new('RGB', (4, 4), 'blue')], duration=50, loop=0)
    with pytest.raises(HTTPException) as error:
        app.decode_image(out.getvalue())
    assert error.value.status_code == 415


def test_only_one_inference_and_release_on_failure(monkeypatch):
    entered, finish = threading.Event(), threading.Event()
    def predict(image):
        entered.set()
        assert finish.wait(5)
        raise ValueError('simulated inference failure')
    monkeypatch.setattr(app, '_predict_image', predict)
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(app.predict_image, None)
        assert entered.wait(5)
        try:
            with pytest.raises(HTTPException) as error:
                app.predict_image(None)
            assert error.value.status_code == 503
        finally:
            finish.set()
        with pytest.raises(ValueError): running.result()
    assert app.INFERENCE_SLOT.acquire(blocking=False)
    app.INFERENCE_SLOT.release()


def run_asgi(messages, headers=(), downstream=None):
    sent = []
    async def go():
        async def receive(): return messages.pop(0)
        async def send(message): sent.append(message)
        async def forbidden(*args): pytest.fail('Rejected body reached parser')
        middleware = limits.RequestLimits(downstream or forbidden)
        await middleware({'type': 'http', 'method': 'POST', 'path': '/predict',
                          'headers': list(headers)}, receive, send)
    asyncio.run(go())
    return sent[0]['status']


def test_chunked_body_limit(monkeypatch):
    monkeypatch.setattr(limits, 'MAX_BODY_BYTES', 8)
    assert run_asgi([{'type': 'http.request', 'body': b'12345', 'more_body': True},
                     {'type': 'http.request', 'body': b'6789', 'more_body': False}]) == 413


def test_declared_size_rejected_without_reading():
    assert run_asgi([], [(b'content-length', b'999999999')]) == 413


def test_body_deadline_and_slot_reuse(monkeypatch):
    monkeypatch.setattr(limits, 'BODY_TIMEOUT_SECONDS', .02)
    async def go():
        sent = []
        async def slow(): await asyncio.sleep(1)
        async def send(message): sent.append(message)
        middleware = limits.RequestLimits(None)
        await middleware({'type': 'http', 'method': 'POST', 'path': '/predict', 'headers': []}, slow, send)
        assert sent[0]['status'] == 408
        assert middleware.slots.acquire(False) and middleware.slots.acquire(False)
    asyncio.run(go())


def test_admission_rejects_before_reading():
    async def go():
        middleware = limits.RequestLimits(None)
        for _ in range(limits.MAX_ACTIVE_REQUESTS): assert middleware.slots.acquire(False)
        sent = []
        async def receive(): pytest.fail('Busy request should not read body')
        async def send(message): sent.append(message)
        await middleware({'type': 'http', 'method': 'POST', 'path': '/predict'}, receive, send)
        assert sent[0]['status'] == 503
    asyncio.run(go())


def test_multipart_count_and_json_limits():
    with TestClient(app.app) as client:
        assert client.post('/predict', files=[('file', ('a.png', b'a')), ('upload', ('b.png', b'b'))]).status_code == 400
        assert client.post('/predict', data={'text': 'a'}, files={'file': ('a.png', b'a')}).status_code == 400
        assert client.post('/predict', json={'url': 'x' * 5000}).status_code == 413
        assert client.post('/predict', data={'url': 'a'}).status_code == 415
