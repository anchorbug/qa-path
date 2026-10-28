"""Bounded feedback runner for the local owner's exercises, not a security sandbox."""
import contextlib
import io
import json
from pathlib import Path
import sys
import traceback


class LimitedOutput(io.TextIOBase):
    def __init__(self):
        self.text = ''

    def write(self, value):
        self.text += value[:max(0, 4000 - len(self.text))]
        return len(value)

    def flush(self):
        pass


folder = Path(sys.argv[1])
output = LimitedOutput()
results = []
error = ''


def check(label, condition):
    results.append({'label': label, 'passed': bool(condition)})


try:
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        namespace = {'__name__': 'student'}
        exec(compile((folder / 'solution.py').read_text(encoding='utf-8'), 'solution.py', 'exec'), namespace)
        namespace['check'] = check
        exec(compile((folder / 'checks.py').read_text(encoding='utf-8'), 'checks.py', 'exec'), namespace)
except BaseException:
    error = traceback.format_exc(limit=4)

(folder / 'result.json').write_text(json.dumps({'passed': bool(results) and all(item['passed'] for item in results) and not error, 'checks': results, 'error': error, 'output': output.text}, ensure_ascii=False), encoding='utf-8')
