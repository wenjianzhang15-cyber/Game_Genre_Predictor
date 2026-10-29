"""Run with pytest after installing requirements plus pytest and httpx.
Uses the real saved model. Local URLs are fixtures for the self-fetch regression.
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
import pytest
import requests
import subprocess
from fastapi.testclient import TestClient
import app

ROOT = Path(__file__).resolve().parents[1]
@pytest.fixture(scope='module')
def client():
    return TestClient(app.app)

@pytest.fixture(scope='module')
def server(tmp_path_factory):
    evidence_dir = tmp_path_factory.mktemp("server-evidence")
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    log = (evidence_dir / 'candidate_server.log').open('w')
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', str(port)], cwd=ROOT, stdout=log, stderr=log)
    try:
        for _ in range(150):
            try:
                if requests.get(base+'/health', timeout=.2).ok: break
            except requests.RequestException: pass
            time.sleep(.1)
        else: raise RuntimeError('Server did not become ready')
        yield base
    finally:
        process.terminate(); process.wait(timeout=10); log.close()

@pytest.mark.parametrize('name,label', [('HollowKnight','platform'),('Stardew','indie'),('moncage','puzzle')])
def test_real_upload_and_self_url_match(server, name, label, tmp_path):
    content = (ROOT/'covers'/f'{name}.jpg').read_bytes()
    uploaded = requests.post(server+'/predict', files={'file':(name+'.jpg',content,'image/jpeg')},timeout=15)
    started=time.monotonic()
    linked = requests.post(server+'/predict', json={'url':f'/ui/covers/{name}.jpg'},timeout=15)
    assert uploaded.status_code == linked.status_code == 200
    assert time.monotonic()-started < 9
    a,b=uploaded.json(),linked.json()
    assert a['label'] == b['label'] == label
    assert a['top_k'] == b['top_k']
    assert len(b['top_k']) == 5
    assert sum(x['prob'] for x in b['top_k']) == pytest.approx(1,abs=1e-6)
    evidence=tmp_path/f'candidate_{name}.json'
    evidence.write_text(json.dumps({'upload':a,'self_url':b},indent=2))

@pytest.mark.parametrize('payload', [{}, [], None, {'url': 123}, {'url':''}, {'url':'not-a-url'}, {'url':'file:///etc/passwd'}, {'url':'https://[invalid'}])
def test_invalid_json_inputs(client,payload):
    r=client.post('/predict',content=json.dumps(payload),headers={'Content-Type':'application/json'})
    assert r.status_code == 400
    assert isinstance(r.json()['detail'],str)

def test_malformed_json(client):
    assert client.post('/predict',content='{',headers={'Content-Type':'application/json'}).status_code == 400

def test_non_image_upload(client):
    assert client.post('/predict',files={'file':('not-image.txt',b'not an image','text/plain')}).status_code == 415

def test_empty_upload(client):
    assert client.post('/predict',files={'file':('empty.jpg',b'','image/jpeg')}).status_code == 415

def test_oversized_upload(client):
    assert client.post('/predict',files={'file':('large.jpg',b'x'*(app.MAX_IMAGE_BYTES+1),'image/jpeg')}).status_code == 413

def test_missing_upload(client):
    assert client.post('/predict').status_code == 400

def test_upload_alias(client):
    data=(ROOT/'covers/HollowKnight.jpg').read_bytes()
    r=client.post('/predict',files={'upload':('cover.jpg',data,'image/jpeg')})
    assert r.status_code==200 and r.json()['label']=='platform'

def test_remote_non_image(server):
    assert requests.post(server+'/predict',json={'url':server+'/ui/index.html'},timeout=15).status_code==400

def test_remote_missing_image(server):
    assert requests.post(server+'/predict',json={'url':server+'/ui/covers/does-not-exist.jpg'},timeout=15).status_code==400

@pytest.mark.parametrize('returncode,expected', [(43,502),(44,504)])
def test_download_failures(client,monkeypatch,returncode,expected):
    def fail(*args,**kwargs): return subprocess.CompletedProcess(args, returncode, stdout=b'')
    monkeypatch.setattr(app.subprocess,'run',fail)
    r=client.post('/predict',json={'url':'https://example.com/cover.jpg'})
    assert r.status_code==expected and 'detail' in r.json()


def test_cors_upload_and_preflight(client):
    headers={'Origin':'https://example.com','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'}
    assert client.options('/predict',headers=headers).status_code==200
    r=client.post('/predict',files={'file':('cover.jpg',(ROOT/'covers/HollowKnight.jpg').read_bytes(),'image/jpeg')},headers={'Origin':'https://example.com'})
    assert r.status_code==200 and r.headers.get('access-control-allow-origin')=='*'
@pytest.mark.parametrize("path", ["/ui/app.py", "/ui/best_model.pth", "/ui/classes.txt", "/ui/.git/config", "/ui/.env", "/ui/requirements.txt"])
def test_private_project_files_not_served(client, path):
    assert client.get(path).status_code == 404

def test_ui_routes(client):
    assert client.get("/").status_code == 200
    assert client.get("/ui/").status_code == 200
    assert client.get("/ui/covers/HollowKnight.jpg").headers["content-type"].startswith("image/")
