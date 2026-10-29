"""Small post-deployment smoke check; does not change hosting settings."""
import argparse
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://legend0908-game-genre-demo.hf.space')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/deployment-check.json')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    checks = []
    session = requests.Session()

    def record(name, response, valid):
        check = {'name': name, 'status': response.status_code, 'passed': bool(valid)}
        checks.append(check)
        if not valid:
            raise RuntimeError(f'{name} failed (HTTP {response.status_code})')

    try:
        response = session.get(base + '/health', timeout=90)
        record('health', response, response.ok and response.json().get('classes') == 5)
        response = session.get(base + '/ui/index.html', timeout=30)
        record('updated_frontend', response, response.ok and 'Top 3 genre matches' in response.text
               and 'HTTPS image URL' in response.text)
        for name, label in [('HollowKnight', 'platform'), ('Stardew', 'indie'), ('moncage', 'puzzle')]:
            response = session.post(base + '/predict', json={'url': f'/ui/covers/{name}.jpg'}, timeout=30)
            data = response.json()
            record(name, response, response.ok and data.get('label') == label and len(data.get('top_k', [])) == 5)
        with (ROOT / 'covers/HollowKnight.jpg').open('rb') as image:
            response = session.post(base + '/predict', files={'file': ('HollowKnight.jpg', image, 'image/jpeg')}, timeout=30)
        record('uploaded_cover', response, response.ok and response.json().get('label') == 'platform')
        for url in ['http://127.0.0.1/', 'https://127.0.0.1/secret']:
            response = session.post(base + '/predict', json={'url': url}, timeout=30)
            record('blocked_' + url, response, response.status_code == 400)
        for path in ['/ui/app.py', '/ui/best_model.pth', '/ui/.git/config']:
            response = session.get(base + path, timeout=15)
            record('private_' + path, response, response.status_code == 404)
    finally:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({'base_url': base, 'checks': checks}, indent=2), encoding='utf-8')
        session.close()
    print(f'{len(checks)} deployed smoke checks passed: {base}')


if __name__ == '__main__':
    main()
