import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import app
from labs import LABS
from training_api import TrainingServer


class WorkshopTests(unittest.TestCase):
    def test_labs_are_not_auto_certified(self):
        self.assertEqual(len(LABS), 20)
        self.assertEqual(len(app.LESSON_MAP), 34)
        for lab in LABS:
            self.assertGreaterEqual(len(lab['theory']), 4)
            self.assertGreaterEqual(len(lab['criteria']), 3)
            with self.assertRaises(ValueError):
                app.evaluate(lab['id'], 'raise RuntimeError("must not execute")')


class TrainingApiTests(unittest.TestCase):
    def setUp(self):
        self.server = TrainingServer(('127.0.0.1', 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, method, path, body=None, user='alice'):
        headers = {'Content-Type': 'application/json'}
        if user:
            headers['Authorization'] = f'Bearer {user}'
        req = Request(self.url + path, method=method, headers=headers,
                      data=json.dumps(body).encode() if body is not None else None)
        try:
            response = urlopen(req, timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_lifecycle_and_boundaries(self):
        for quantity in (1, 99):
            status, order = self.request('POST', '/orders', {'quantity': quantity})
            self.assertEqual(status, 201)
            self.assertEqual(order['total'], quantity * 500)
            path = f'/orders/{order["id"]}'
            self.assertEqual(self.request('GET', path), (200, order))
            status, changed = self.request('PATCH', path, {'quantity': 3})
            self.assertEqual((status, changed['quantity'], changed['total']), (200, 3, 1500))
            self.assertEqual(self.request('GET', path), (200, changed))
            self.assertEqual(self.request('DELETE', path)[0], 200)
            self.assertEqual(self.request('GET', path)[0], 404)
            self.assertEqual(self.request('DELETE', path)[0], 404)

    def test_rejected_data_does_not_change_state(self):
        _, order = self.request('POST', '/orders', {'quantity': 2})
        path = f'/orders/{order["id"]}'
        for body in ({}, [], {'quantity': 0}, {'quantity': -1}, {'quantity': 100},
                     {'quantity': 1.5}, {'quantity': '2'}, {'quantity': True}, {'quantity': None}):
            with self.subTest(body=body):
                self.assertEqual(self.request('POST', '/orders', body)[0], 400)
                self.assertEqual(self.request('PATCH', path, body)[0], 400)
                self.assertEqual(self.request('GET', path), (200, order))
        self.assertEqual(self.request('GET', '/orders'), (200, {'orders': [order]}))

    def test_authorization_isolation_and_no_mutation(self):
        _, order = self.request('POST', '/orders', {'quantity': 2})
        path = f'/orders/{order["id"]}'
        for method in ('GET', 'PATCH', 'DELETE'):
            self.assertEqual(self.request(method, path, {'quantity': 99}, user='bob')[0], 403)
            self.assertEqual(self.request(method, path, {'quantity': 99}, user=None)[0], 401)
        self.assertEqual(self.request('GET', '/orders', user='bob'), (200, {'orders': []}))
        self.assertEqual(self.request('GET', path), (200, order))

    def test_health_unknown_and_wrong_method(self):
        self.assertEqual(self.request('GET', '/health', user=None), (200, {'status': 'ok'}))
        self.assertEqual(self.request('GET', '/unknown')[0], 404)
        self.assertEqual(self.request('GET', '/orders/nope')[0], 404)
        self.assertEqual(self.request('PATCH', '/orders', {'quantity': 2})[0], 405)
