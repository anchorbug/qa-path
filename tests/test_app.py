import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app
from course import LESSONS


SOLUTIONS = {
    '01-first-check': 'price = 750\nquantity = 3\nactual = price * quantity\nassert actual == 2250',
    '02-types': 'def cart_total(price_text, quantity):\n    return int(price_text) * quantity',
    '03-boundaries': 'def delivery_cost(total):\n    return 0 if total >= 3000 else 250',
    '04-dictionaries': 'def is_paid_order(response, expected_total):\n    return response.get("status") == "paid" and response.get("total") == expected_total',
    '05-loops': 'def server_errors(statuses):\n    return [s for s in statuses if 500 <= s <= 599]',
    '06-errors': 'def parse_quantity(text):\n    try:\n        value = int(text)\n        return value if value > 0 else None\n    except ValueError:\n        return None',
    '07-json': 'import json\ndef product_ids(text):\n    return [item["id"] for item in json.loads(text)["items"]]',
    '08-git': 'commands = ["git status", "git add test_cart.py", \'git commit -m "Add cart test"\', "git push"]',
    '09-pytest': 'def delivery_cost(total):\n    return 0 if total >= 3000 else 250\ndef test_delivery_boundary():\n    assert delivery_cost(3000) == 0',
    '10-api': 'def validate_catalog(status_code, body):\n    assert status_code == 200\n    products = body.get("products")\n    assert isinstance(products, list)\n    assert products\n    assert type(products[0]["id"]) is int\n    assert products[0]["price"] > 0',
    '11-isolation': 'def new_cart():\n    return {"items": [], "currency": "GEL"}',
    '12-sql': 'query = "SELECT id FROM orders WHERE status = ? AND total >= ? ORDER BY id"\nparameters = ("paid", 1000)',
    '13-ui': 'plan = {"role":"button","name":"Добавить блокнот","quantity":"2","expected_total":"1000"}',
    '14-final': 'def test_cart_total():\n    response = cart_api(500, 2)\n    assert response["quantity"] == 2\n    assert response["total"] == 1000',
}


class CourseTests(unittest.TestCase):
    def test_reference_solutions_pass(self):
        self.assertEqual(set(SOLUTIONS), set(app.LESSON_MAP))
        for lesson_id, code in SOLUTIONS.items():
            with self.subTest(lesson=lesson_id):
                result = app.evaluate(lesson_id, code)
                self.assertTrue(result['passed'], result)

    def test_unfinished_starters_fail(self):
        for lesson in LESSONS:
            with self.subTest(lesson=lesson['id']):
                self.assertFalse(app.evaluate(lesson['id'], lesson['starter'])['passed'])

    def test_final_rejects_test_without_assertions(self):
        result = app.evaluate('14-final', 'def test_cart_total():\n    cart_api(500, 2)')
        self.assertFalse(result['passed'])
        self.assertEqual([c['passed'] for c in result['checks']], [True, False, False])

    def test_final_rejects_quantity_blind_test(self):
        result = app.evaluate('14-final', 'def test_cart_total():\n    assert cart_api(500, 2)["total"] == 1000')
        self.assertFalse(result['passed'])
        self.assertEqual([c['passed'] for c in result['checks']], [True, True, False])

    def test_errors_are_returned(self):
        result = app.evaluate('02-types', 'def broken(:')
        self.assertFalse(result['passed'])
        self.assertIn('SyntaxError', result['error'])

    def test_timeout_is_bounded(self):
        result = app.evaluate('02-types', 'while True: pass')
        self.assertFalse(result['passed'])
        self.assertIn('8 секунд', result['error'])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_data = app.DATA
        app.DATA = Path(self.temp.name)
        self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        app.DATA = self.old_data
        self.temp.cleanup()

    def request(self, path, payload=None, token=True):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-QA-Token'] = app.TOKEN
        request = Request(self.url + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
        with urlopen(request, timeout=12) as response:
            return json.load(response)

    def test_course_hides_checks(self):
        data = self.request('/api/course')
        self.assertEqual(len(data['lessons']), 14)
        self.assertNotIn('checks', data['lessons'][0])
        self.assertEqual(data['progress'], {})

    def test_check_persists_and_failure_does_not_erase_achievement(self):
        payload = {'lesson':'02-types','code':SOLUTIONS['02-types'],'hints':1}
        result = self.request('/api/check', payload)
        self.assertTrue(result['result']['passed'])
        payload['code'] = 'def cart_total(a,b): return 0'
        self.request('/api/check', payload)
        record = self.request('/api/course')['progress']['02-types']
        self.assertEqual(record['attempts'], 2)
        self.assertEqual(record['passed'], 1)
        self.assertEqual(record['hints'], 1)
        self.assertEqual(record['code'], payload['code'])
        self.assertEqual(len(self.request('/api/history')), 2)

    def test_export_import_round_trip(self):
        self.request('/api/save', {'lesson':'03-boundaries','code':'# Привет','hints':1})
        backup = self.request('/api/export')
        self.request('/api/save', {'lesson':'03-boundaries','code':'changed','hints':0})
        result = self.request('/api/import', backup)
        self.assertEqual(result['progress']['03-boundaries']['code'], '# Привет')
        self.assertEqual(result['progress']['03-boundaries']['hints'], 1)

    def test_invalid_import_is_atomic(self):
        self.request('/api/save', {'lesson':'03-boundaries','code':'original','hints':0})
        with self.assertRaises(HTTPError) as caught:
            self.request('/api/import', {'version':1,'progress':{'03-boundaries':{'code':'changed'},'unknown':{'code':''}}})
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(self.request('/api/course')['progress']['03-boundaries']['code'], 'original')

    def test_token_is_required(self):
        with self.assertRaises(HTTPError) as caught:
            self.request('/api/save', {'lesson':'02-types','code':'x'}, token=False)
        self.assertEqual(caught.exception.code, 403)

    def test_shop_and_unknown_path(self):
        self.assertEqual(len(self.request('/shop/api/products')['products']), 2)
        with self.assertRaises(HTTPError) as caught:
            self.request('/shop/api/missing')
        self.assertEqual(caught.exception.code, 404)


if __name__ == '__main__':
    unittest.main()
