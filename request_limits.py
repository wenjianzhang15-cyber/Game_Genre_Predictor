"""ASGI admission control before JSON or multipart parsing."""
import asyncio
import threading
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 8 * 1024 * 1024 + 64 * 1024
MAX_JSON_BYTES = 4096
BODY_TIMEOUT_SECONDS = 15
MAX_ACTIVE_REQUESTS = 2


class RequestLimits:
    def __init__(self, app):
        self.app = app
        self.slots = threading.BoundedSemaphore(MAX_ACTIVE_REQUESTS)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] != '/predict' or scope['method'] != 'POST':
            return await self.app(scope, receive, send)
        async def reject(status, detail):
            await JSONResponse({'detail': detail}, status_code=status,
                               headers={'Retry-After': '2'} if status == 503 else None)(scope, receive, send)
        if not self.slots.acquire(blocking=False):
            return await reject(503, 'The model is busy. Please try again shortly.')
        try:
            headers = scope.get('headers', [])
            types = [v.decode('latin1').split(';')[0].strip().lower() for k, v in headers if k == b'content-type']
            content_type = types[0] if len(types) == 1 else ''
            if any(k == b'content-encoding' and v.lower() != b'identity' for k, v in headers):
                return await reject(415, 'Compressed request bodies are not supported.')
            limit = MAX_JSON_BYTES if content_type == 'application/json' else MAX_BODY_BYTES
            lengths = [v for k, v in headers if k == b'content-length']
            if lengths:
                if len(lengths) != 1 or not lengths[0].isdigit():
                    return await reject(400, 'Invalid request length.')
                if int(lengths[0]) > limit:
                    return await reject(413, 'The request is too large.')
            body = bytearray()
            try:
                # One absolute deadline, not a fresh timeout for each chunk.
                async with asyncio.timeout(BODY_TIMEOUT_SECONDS):
                    while True:
                        message = await receive()
                        if message['type'] == 'http.disconnect':
                            return
                        chunk = message.get('body', b'')
                        if len(body) + len(chunk) > limit:
                            return await reject(413, 'The request is too large.')
                        body.extend(chunk)
                        if not message.get('more_body', False):
                            break
            except TimeoutError:
                return await reject(408, 'The upload took too long. Please try again.')
            if lengths and len(body) != int(lengths[0]):
                return await reject(400, 'Request length does not match the body.')
            delivered = False
            async def replay():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()
            await self.app(scope, replay, send)
        finally:
            self.slots.release()
