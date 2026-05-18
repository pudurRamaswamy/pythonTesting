import pytest
from playwright.sync_api import sync_playwright
from pydantic import ValidationError

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

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Global hook to handle failures.
    1. If it's a Contract violation (Pydantic), it prints the JSON error.
    2. If it's a UI failure, it captures a screenshot (if a page is available).
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # Check for Pydantic Contract Violations
        if call.excinfo and isinstance(call.excinfo.value, ValidationError):
            print("\n" + "!"*50)
            print("CONTRACT ERROR: The API response does not match the model!")
            print(call.excinfo.value.json())
            print("!"*50)
            
        # Check for UI Failures to take a screenshot
        # 'page' is retrieved from the test's arguments
        if "authenticated_page" in item.funcargs:
            page = item.funcargs["authenticated_page"]
            screenshot_path = f"failure_{item.name}.png"
            page.screenshot(path=screenshot_path)
            print(f"Screenshot saved to {screenshot_path}")