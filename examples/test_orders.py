"""Compare after attempting workshop 25. Tests use a real local HTTP server."""
import pytest
import requests


@pytest.fixture
def alice():
    with requests.Session() as session:
        session.headers['Authorization'] = 'Bearer alice'
        yield session


@pytest.fixture
def order(alice, orders_url):
    response = alice.post(f'{orders_url}/orders', json={'quantity': 2}, timeout=5)
    assert response.status_code == 201
    created = response.json()
    try:
        yield created
    finally:
        response = alice.delete(f'{orders_url}/orders/{created["id"]}', timeout=5)
        assert response.status_code in (200, 404)


def test_lifecycle(alice, orders_url, order):
    url = f'{orders_url}/orders/{order["id"]}'
    read = alice.get(url, timeout=5)
    assert read.status_code == 200
    assert read.json() == order
    changed = alice.patch(url, json={'quantity': 3}, timeout=5)
    assert changed.status_code == 200
    assert changed.json()['total'] == 1500
    assert alice.get(url, timeout=5).json()['quantity'] == 3
    assert alice.delete(url, timeout=5).status_code == 200
    assert alice.get(url, timeout=5).status_code == 404


@pytest.mark.parametrize('quantity', [0, -1, 100, 1.5, '2', True, None])
def test_invalid_quantity_does_not_create(alice, orders_url, quantity):
    url = f'{orders_url}/orders'
    before = alice.get(url, timeout=5).json()
    response = alice.post(url, json={'quantity': quantity}, timeout=5)
    assert response.status_code == 400
    assert response.json() == {'error': 'invalid_quantity'}
    assert alice.get(url, timeout=5).json() == before


@pytest.mark.parametrize('method', ['get', 'patch', 'delete'])
def test_other_user_cannot_access(alice, orders_url, order, method):
    url = f'{orders_url}/orders/{order["id"]}'
    response = requests.request(method, url, headers={'Authorization': 'Bearer bob'},
                                json={'quantity': 99}, timeout=5)
    assert response.status_code == 403
    assert alice.get(url, timeout=5).json() == order
