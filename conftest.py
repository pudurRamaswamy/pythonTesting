import pytest
from playwright.sync_api import sync_playwright

@pytest.fixture(scope="session")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()

@pytest.fixture(scope="function")
def authenticated_page(browser_instance):
    # Isolated context for every test
    context = browser_instance.new_context()
    page = context.new_page()
    yield page
    context.close()