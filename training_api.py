"""Local, in-memory exercise service. Fake identities, never production auth."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from urllib.parse import urlparse


class TrainingServer(ThreadingHTTPServer):
    def __init__(self, address):
        super().__init__(address, Handler)
        self.orders = {}
        self.next_id = 1
        self.lock = Lock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_request(self):
        path = urlparse(self.path).path
        if path == '/health' and self.command == 'GET':
            return self.reply(200, {'status': 'ok'})
        token = self.headers.get('Authorization', '')
        if token not in ('Bearer alice', 'Bearer bob'):
            return self.reply(401, {'error': 'unauthorized'})
        owner = token.split()[1]
        if path != '/orders' and not path.startswith('/orders/'):
            return self.reply(404, {'error': 'not_found'})
        order_id = None
        if path != '/orders':
            try:
                order_id = int(path.removeprefix('/orders/'))
            except ValueError:
                return self.reply(404, {'error': 'not_found'})
        if (order_id is None and self.command not in ('GET', 'POST')) or (order_id is not None and self.command not in ('GET', 'PATCH', 'DELETE')):
            return self.reply(405, {'error': 'method_not_allowed'})
        with self.server.lock:
            order = self.server.orders.get(order_id)
            if order_id is not None:
                if order is None:
                    return self.reply(404, {'error': 'not_found'})
                if order['owner'] != owner:
                    return self.reply(403, {'error': 'forbidden'})
            if self.command in ('POST', 'PATCH'):
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 4096:
                        raise ValueError('length')
                    body = json.loads(self.rfile.read(length))
                    quantity = body.get('quantity') if isinstance(body, dict) else None
                    if type(quantity) is not int or not 1 <= quantity <= 99:
                        raise ValueError('quantity')
                except (ValueError, UnicodeError):
                    return self.reply(400, {'error': 'invalid_quantity'})
                if self.command == 'POST':
                    order_id = self.server.next_id
                    self.server.next_id += 1
                order = {'id': order_id, 'owner': owner, 'quantity': quantity, 'total': quantity * 500}
                self.server.orders[order_id] = order
                return self.reply(201 if self.command == 'POST' else 200, order)
            if self.command == 'DELETE':
                del self.server.orders[order_id]
                return self.reply(200, {'deleted': order_id})
            if order_id is not None:
                return self.reply(200, order)
            return self.reply(200, {'orders': [v for v in self.server.orders.values() if v['owner'] == owner]})

    do_GET = handle_request
    do_POST = handle_request
    do_PATCH = handle_request
    do_DELETE = handle_request


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8767)
    args = parser.parse_args()
    server = TrainingServer(('127.0.0.1', args.port))
    print(f'Training API: http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
