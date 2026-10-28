"""QA Path: local learning application. Python 3.11+, no runtime dependencies."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from contextlib import contextmanager
import argparse
import json
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import webbrowser

from course import LESSONS

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
TOKEN = secrets.token_urlsafe(32)
RUN_LOCK = threading.Lock()
LESSON_MAP = {lesson['id']: lesson for lesson in LESSONS}


@contextmanager
def connect():
    DATA.mkdir(exist_ok=True)
    db = sqlite3.connect(DATA / 'progress.sqlite3')
    try:
        db.row_factory = sqlite3.Row
        with db:
            db.execute('CREATE TABLE IF NOT EXISTS progress (lesson TEXT PRIMARY KEY, code TEXT NOT NULL, passed INTEGER NOT NULL DEFAULT 0, hints INTEGER NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0, updated TEXT DEFAULT CURRENT_TIMESTAMP)')
            db.execute('CREATE TABLE IF NOT EXISTS attempts (id INTEGER PRIMARY KEY, lesson TEXT NOT NULL, passed INTEGER NOT NULL, feedback TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP)')
            yield db
    finally:
        db.close()


def state():
    with connect() as db:
        return {row['lesson']: dict(row) for row in db.execute('SELECT * FROM progress')}


def save(lesson, code, hints=0, result=None):
    with connect() as db:
        db.execute('INSERT INTO progress(lesson,code,hints) VALUES(?,?,?) ON CONFLICT(lesson) DO UPDATE SET code=excluded.code,hints=MAX(progress.hints,excluded.hints),updated=CURRENT_TIMESTAMP', (lesson, code, hints))
        if result is not None:
            db.execute('UPDATE progress SET passed=MAX(passed,?),attempts=attempts+1 WHERE lesson=?', (int(result['passed']), lesson))
            db.execute('INSERT INTO attempts(lesson,passed,feedback) VALUES(?,?,?)', (lesson, int(result['passed']), json.dumps(result, ensure_ascii=False)))


def evaluate(lesson_id, code):
    """Run learner-owned local Python in a separate process; this is NOT a sandbox."""
    lesson = LESSON_MAP[lesson_id]
    if lesson.get('kind') == 'lab':
        raise ValueError('Эта работа выполняется в IDE и принимается по отчёту. Автопроверки нет.')
    with tempfile.TemporaryDirectory(prefix='qa-path-') as temp:
        folder = Path(temp)
        (folder / 'solution.py').write_text(code, encoding='utf-8')
        (folder / 'checks.py').write_text(lesson['checks'], encoding='utf-8')
        runner = ROOT / 'runner.py'
        try:
            run = subprocess.run([sys.executable, '-I', str(runner), str(folder)], cwd=folder,
                                 capture_output=True, timeout=8, encoding='utf-8', errors='replace')
            result_file = folder / 'result.json'
            if result_file.exists():
                return json.loads(result_file.read_text(encoding='utf-8'))
            return {'passed': False, 'checks': [], 'error': (run.stderr or run.stdout or 'Процесс завершился без результата.')[-4000:]}
        except subprocess.TimeoutExpired:
            return {'passed': False, 'checks': [], 'error': 'Превышено 8 секунд. Проверь условие выхода из цикла и сетевые ожидания.'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, data, status=200, content_type='application/json; charset=utf-8'):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8') if not isinstance(data, bytes) else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        host = self.headers.get('Host', '').split(':')[0]
        if host not in ('127.0.0.1', 'localhost'):
            return self.respond({'error': 'Local access only'}, 403)
        path = urlparse(self.path).path
        if path == '/api/course':
            return self.respond({'lessons': [{k: v for k, v in item.items() if k != 'checks'} for item in LESSONS], 'progress': state(), 'token': TOKEN, 'workspace': str(ROOT / 'workspace')})
        if path == '/api/export':
            return self.respond({'version': 1, 'progress': state()})
        if path == '/api/history':
            with connect() as db:
                rows = [dict(row) for row in db.execute('SELECT lesson,passed,feedback,created FROM attempts ORDER BY id DESC LIMIT 30')]
            return self.respond(rows)
        if path == '/shop/api/products':
            return self.respond({'products': [{'id': 1, 'name': 'QA Notebook', 'price': 500}, {'id': 2, 'name': 'Debug Mug', 'price': 750}]})
        assets = {'/': ('index.html', 'text/html'), '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css'), '/shop': ('shop.html', 'text/html')}
        if path in assets:
            name, mime = assets[path]
            return self.respond((ROOT / 'static' / name).read_bytes(), content_type=mime + '; charset=utf-8')
        return self.respond({'error': 'Not found'}, 404)

    def do_POST(self):
        if self.headers.get('X-QA-Token') != TOKEN:
            return self.respond({'error': 'Обнови страницу приложения.'}, 403)
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length < 0 or length > 500_000:
                raise ValueError('Слишком большой запрос.')
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError('Ожидался объект JSON.')
            path = urlparse(self.path).path
            if path == '/api/import':
                if payload.get('version') != 1 or not isinstance(payload.get('progress'), dict):
                    raise ValueError('Неподдерживаемая резервная копия.')
                records = []
                for key, item in payload['progress'].items():
                    if key not in LESSON_MAP or not isinstance(item, dict):
                        raise ValueError('Неизвестный урок в резервной копии.')
                    code = item.get('code', '')
                    if not isinstance(code, str) or len(code) > 30_000:
                        raise ValueError('Некорректный код в резервной копии.')
                    hints = int(item.get('hints', 0))
                    attempts = int(item.get('attempts', 0))
                    if hints < 0 or hints > len(LESSON_MAP[key]['hints']) or attempts < 0:
                        raise ValueError('Некорректный прогресс.')
                    records.append((key, code, int(bool(item.get('passed'))), hints, attempts))
                with connect() as db:
                    db.executemany('INSERT INTO progress(lesson,code,passed,hints,attempts) VALUES(?,?,?,?,?) ON CONFLICT(lesson) DO UPDATE SET code=excluded.code,passed=MAX(progress.passed,excluded.passed),hints=MAX(progress.hints,excluded.hints),attempts=MAX(progress.attempts,excluded.attempts)', records)
                return self.respond({'progress': state()})
            lesson_id = payload.get('lesson')
            code = payload.get('code', '')
            if lesson_id not in LESSON_MAP or not isinstance(code, str) or len(code) > 30_000:
                raise ValueError('Неизвестный урок или слишком большой код.')
            hints = int(payload.get('hints', 0))
            if hints < 0 or hints > len(LESSON_MAP[lesson_id]['hints']):
                raise ValueError('Некорректное число подсказок.')
            if path == '/api/save':
                save(lesson_id, code, hints)
                return self.respond({'saved': True})
            if path == '/api/file':
                folder = ROOT / 'workspace'
                folder.mkdir(exist_ok=True)
                suffix = '.md' if LESSON_MAP[lesson_id].get('kind') == 'lab' else '.py'
                target = folder / (lesson_id + suffix)
                if payload.get('read'):
                    if not target.exists():
                        raise ValueError('Сначала сохрани файл для редактора.')
                    return self.respond({'code': target.read_text(encoding='utf-8')})
                target.write_text(code, encoding='utf-8')
                return self.respond({'path': str(target)})
            if path == '/api/check':
                if not RUN_LOCK.acquire(blocking=False):
                    return self.respond({'error': 'Другая проверка ещё выполняется.'}, 409)
                try:
                    result = evaluate(lesson_id, code)
                    save(lesson_id, code, hints, result)
                    return self.respond({'result': result, 'progress': state()})
                finally:
                    RUN_LOCK.release()
            return self.respond({'error': 'Not found'}, 404)
        except (ValueError, TypeError, OSError) as error:
            return self.respond({'error': str(error)}, 400)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    with connect():
        pass
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{args.port}'
    print(f'QA Path: {url}\nStop: Ctrl+C', flush=True)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
