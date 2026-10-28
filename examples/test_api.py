"""Start app.py before running these tests."""
import os
import requests

BASE_URL = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8765')


def test_catalog_contract():
    response = requests.get(f'{BASE_URL}/shop/api/products', timeout=5)
    assert response.status_code == 200
    products = response.json()['products']
    assert len(products) == 2
    for product in products:
        assert type(product['id']) is int
        assert product['price'] > 0


def test_missing_resource():
    response = requests.get(f'{BASE_URL}/shop/api/missing', timeout=5)
    assert response.status_code == 404

