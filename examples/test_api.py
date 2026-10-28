"""A local app is started by conftest; QA_BASE_URL can override it."""
import requests



def test_catalog_contract(shop_url):
    response = requests.get(f'{shop_url}/shop/api/products', timeout=5)
    assert response.status_code == 200
    products = response.json()['products']
    assert len(products) == 2
    for product in products:
        assert type(product['id']) is int
        assert product['price'] > 0


def test_missing_resource(shop_url):
    response = requests.get(f'{shop_url}/shop/api/missing', timeout=5)
    assert response.status_code == 404

