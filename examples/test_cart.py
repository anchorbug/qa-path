"""Run with: python -m pytest examples/test_cart.py -v."""
import pytest


def cart_total(price, quantity):
    return price * quantity


@pytest.mark.parametrize('price, quantity, expected', [(500, 1, 500), (500, 2, 1000), (750, 3, 2250)])
def test_cart_total(price, quantity, expected):
    assert cart_total(price, quantity) == expected

