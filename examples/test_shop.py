"""Start app.py and install Playwright Chromium before running these tests."""
import os
from playwright.sync_api import expect

BASE_URL = os.environ.get('QA_BASE_URL', 'http://127.0.0.1:8765')


def test_two_notebooks(page):
    page.goto(f'{BASE_URL}/shop')
    page.get_by_role('button', name='Добавить блокнот').click()
    page.get_by_label('Количество').fill('2')
    expect(page.get_by_test_id('total')).to_have_text('1000')


def test_invalid_quantity(page):
    page.goto(f'{BASE_URL}/shop')
    page.get_by_role('button', name='Добавить блокнот').click()
    page.get_by_label('Количество').fill('0')
    expect(page.get_by_role('alert')).to_have_text('Введи целое количество от 1 до 99.')
    expect(page.get_by_test_id('total')).to_have_text('—')

