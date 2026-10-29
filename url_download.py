"""Isolated HTTPS downloader. Never imports the model or application.

The parent imposes a hard process deadline, including DNS and slow headers.
DNS is resolved once; TLS connects to the validated numeric address while
retaining the original hostname for certificate verification and SNI.
"""
import ipaddress
import json
import socket
import sys
from urllib.parse import urlsplit

import certifi
import urllib3

MAX_BYTES = 8 * 1024 * 1024
MAX_URL_LENGTH = 2048


class DownloadError(Exception):
    def __init__(self, status):
        self.status = status


def validate_url(url):
    if not isinstance(url, str) or not url or len(url) > MAX_URL_LENGTH:
        raise DownloadError(400)
    if any(ord(c) <= 32 or ord(c) == 127 for c in url) or '\\' in url:
        raise DownloadError(400)
    try:
        parts = urlsplit(url)
        if (parts.scheme != 'https' or not parts.hostname or parts.username is not None
                or parts.password is not None or parts.port not in (None, 443)
                or parts.fragment):
            raise ValueError()
        host = parts.hostname.encode('idna').decode('ascii')
        if '%' in host or host.endswith('.'):
            raise ValueError()
    except (ValueError, UnicodeError):
        raise DownloadError(400) from None
    return host, (parts.path or '/') + ('?' + parts.query if parts.query else '')


def public_address(host):
    try:
        answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        raise DownloadError(502) from None
    addresses = [item[4][0] for item in answers]
    if not addresses:
        raise DownloadError(502)
    for address in addresses:
        ip = ipaddress.ip_address(address)
        # Reject mapped/transition addresses as well as any mixed private DNS answer.
        if (not ip.is_global or ip.is_multicast or ip.is_reserved
                or getattr(ip, 'ipv4_mapped', None) is not None
                or getattr(ip, 'sixtofour', None) is not None
                or getattr(ip, 'teredo', None) is not None):
            raise DownloadError(400)
    return addresses[0]


def fetch(url):
    host, target = validate_url(url)
    address = public_address(host)
    # No ProxyManager, environment proxies, redirects, retries, or second DNS lookup.
    pool = urllib3.HTTPSConnectionPool(
        address, port=443, server_hostname=host, assert_hostname=host,
        cert_reqs='CERT_REQUIRED', ca_certs=certifi.where(),
        timeout=urllib3.Timeout(connect=3, read=3), retries=False,
        maxsize=1, block=True,
    )
    try:
        with pool.request('GET', target, headers={
            'Host': host, 'Accept': 'image/*', 'Accept-Encoding': 'identity',
            'User-Agent': 'GameGenrePredictor/1.0',
        }, redirect=False, preload_content=False, decode_content=False) as response:
            if response.status != 200:
                raise DownloadError(400)
            if response.headers.get('Content-Encoding', 'identity').lower() != 'identity':
                raise DownloadError(415)
            if not response.headers.get('Content-Type', '').lower().startswith('image/'):
                raise DownloadError(415)
            length = response.headers.get('Content-Length')
            if length is not None:
                try:
                    size = int(length)
                except ValueError:
                    raise DownloadError(400) from None
                if size < 0:
                    raise DownloadError(400)
                if size > MAX_BYTES:
                    raise DownloadError(413)
            content = bytearray()
            while True:
                chunk = response.read(min(65536, MAX_BYTES + 1 - len(content)), decode_content=False)
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > MAX_BYTES:
                    raise DownloadError(413)
            return bytes(content)
    except urllib3.exceptions.TimeoutError:
        raise DownloadError(504) from None
    except (urllib3.exceptions.HTTPError, OSError):
        raise DownloadError(502) from None
    finally:
        pool.close()


STATUS_EXIT = {400: 40, 413: 41, 415: 42, 502: 43, 504: 44}

if __name__ == '__main__':
    try:
        payload = json.loads(sys.stdin.buffer.read(8192))
        sys.stdout.buffer.write(fetch(payload['url']))
    except DownloadError as error:
        sys.exit(STATUS_EXIT[error.status])
    except Exception:
        # Do not disclose resolved network addresses, URLs, or internal tracebacks.
        sys.exit(43)
