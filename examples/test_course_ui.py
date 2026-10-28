"""Regression for workshop navigation and persistent, non-executed reports."""
from playwright.sync_api import expect


def test_workshop_report_survives_reload(page, shop_url):
    page.goto(shop_url)
    expect(page.locator('.lesson-link')).to_have_count(34)
    page.locator('[data-id="15-lab"]').click()
    expect(page.get_by_role('heading', name='Критерии приёмки')).to_be_visible()
    expect(page.locator('#check')).to_have_count(0)
    report = 'Проверено: pytest. <script>throw new Error("unsafe")</script>'
    page.get_by_label('Отчёт по лабораторной').fill(report)
    expect(page.locator('#save-state')).to_have_text('✓ Сохранено на компьютере')
    page.reload()
    expect(page.get_by_label('Отчёт по лабораторной')).to_have_value(report)
    expect(page.locator('#progress-label')).to_have_text('0 / 34')
    page.locator('#lab-complete').click()
    expect(page.locator('#progress-label')).to_have_text('1 / 34')
    page.reload()
    expect(page.locator('#progress-label')).to_have_text('1 / 34')
    page.locator('#lab-complete').click()
    expect(page.locator('#progress-label')).to_have_text('0 / 34')
    assert page.locator('.quiet').evaluate('(el) => parseFloat(getComputedStyle(el).fontSize)') >= 14
    page.locator('[data-id="01-first-check"]').click()
    page.get_by_role('button', name='Перейти к практике').click()
    expect(page.locator('#check')).to_be_visible()
