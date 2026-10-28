"""Install Playwright Chromium; conftest starts the local app."""
from playwright.sync_api import expect



def test_two_notebooks(page, shop_url):
    page.goto(f'{shop_url}/shop')
    page.get_by_role('button', name='Добавить блокнот').click()
    page.get_by_label('Количество').fill('2')
    expect(page.get_by_test_id('total')).to_have_text('1000')


def test_invalid_quantity(page, shop_url):
    page.goto(f'{shop_url}/shop')
    page.get_by_role('button', name='Добавить блокнот').click()
    page.get_by_label('Количество').fill('0')
    expect(page.get_by_role('alert')).to_have_text('Введи целое количество от 1 до 99.')
    expect(page.get_by_test_id('total')).to_have_text('—')

