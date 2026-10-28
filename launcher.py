"""Start/stop this checkout's local server without a persistent console window."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import Request, urlopen
import webbrowser

ROOT = Path(__file__).resolve().parent


def probe(url):
    try:
        with urlopen(url + '/api/course', timeout=1) as response:
            data = json.load(response)
        if Path(data.get('workspace', '')).resolve() != ROOT / 'workspace':
            raise RuntimeError('Этот порт занят другой копией курса. Используй другой --port.')
        return data
    except (URLError, TimeoutError, ConnectionError):
        return None
    except (ValueError, KeyError) as error:
        raise RuntimeError('Порт занят другим приложением.') from error


def launch(port=8765, stop=False, open_browser=True):
    url = f'http://127.0.0.1:{port}'
    state = probe(url)
    if stop:
        if state:
            request = Request(url + '/api/shutdown', data=b'{}',
                              headers={'Content-Type': 'application/json', 'X-QA-Token': state['token']})
            with urlopen(request, timeout=3) as response:
                json.load(response)
            for _ in range(50):
                if probe(url) is None:
                    break
                time.sleep(.1)
            else:
                raise RuntimeError('Сервер ещё завершает работу. Повтори остановку позже.')
        print('QA Path stopped. Saved progress is kept.')
        return
    if not state:
        log_dir = ROOT / 'data'
        log_dir.mkdir(exist_ok=True)
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        with (log_dir / 'server.log').open('ab') as log:
            process = subprocess.Popen([sys.executable, str(ROOT / 'app.py'), '--no-browser', '--port', str(port)],
                                       cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options)
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError('Не удалось запустить сервер. Подробности: data/server.log')
            if probe(url):
                break
            time.sleep(.1)
        else:
            process.terminate()
            process.wait(timeout=5)
            raise RuntimeError('Сервер не запустился вовремя. Подробности: data/server.log')
    if open_browser:
        webbrowser.open(url)
    print(f'QA Path: {url}. Stop with stop.bat.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop'], nargs='?', default='start')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        launch(args.port, args.action == 'stop', not args.no_browser)
    except (RuntimeError, OSError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
