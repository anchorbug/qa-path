from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from urllib.request import urlopen


class LauncherTests(unittest.TestCase):
    def test_server_survives_launcher_and_reuses_port_then_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = Path(__file__).resolve().parents[1]
            for name in ('launcher.py', 'app.py', 'course.py', 'labs.py'):
                shutil.copyfile(source / name, folder / name)
            with socket.socket() as available:
                available.bind(('127.0.0.1', 0))
                port = available.getsockname()[1]
            command = [sys.executable, str(folder / 'launcher.py')]

            def run(action):
                result = subprocess.run(command + [action, '--port', str(port), '--no-browser'],
                                        capture_output=True, text=True, timeout=25)
                self.assertEqual(result.returncode, 0, result.stderr)

            try:
                run('start')
                with urlopen(f'http://127.0.0.1:{port}/api/course', timeout=3) as response:
                    self.assertEqual(response.status, 200)
                run('start')  # Must reopen, not create a second process on the port.
            finally:
                run('stop')
            with self.assertRaises(OSError):
                urlopen(f'http://127.0.0.1:{port}/api/course', timeout=1)
            run('stop')  # Already stopped is harmless.
