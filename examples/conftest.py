"""Self-contained API/UI example runs; no manually started app required."""
import os
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app
from training_api import TrainingServer


@pytest.fixture(scope='session')
def shop_url(tmp_path_factory):
    external = os.environ.get('QA_BASE_URL')
    if external:
        yield external.rstrip('/')
        return
    old_data = app.DATA
    app.DATA = tmp_path_factory.mktemp('course-data')
    server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
        app.DATA = old_data


@pytest.fixture(scope='session')
def orders_url():
    server = TrainingServer(('127.0.0.1', 0))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
