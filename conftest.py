"""Session-level fixtures and global hooks shared by every test module.

Architectural decisions encoded here:
- browser_instance is session-scoped: one browser process for the entire run.
- authenticated_page is function-scoped: fresh context per test for isolation.
- valid_user_list_response / invalid_schema_cases supply deterministic mock
  data so contract tests never depend on a live external API.
- The pytest_runtest_makereport hook provides uniform failure reporting:
  Pydantic errors get pretty-printed JSON; UI failures get a screenshot.
"""

import os
import pytest
from playwright.sync_api import sync_playwright
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE_URL = "https://reqres.in/api"

# Optional API key loaded from the environment (reqres.in started requiring one).
# Set REQRES_API_KEY in your shell or CI secrets to enable live-API tests.
REQRES_API_KEY = os.environ.get("REQRES_API_KEY", "")


# ---------------------------------------------------------------------------
# Browser / page fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def browser_instance():
    """Launch one Chromium process for the whole test session.

    Session scope keeps startup cost low. Contexts are still isolated
    per-test via authenticated_page below.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture(scope="function")
def authenticated_page(browser_instance):
    """Return a fresh browser page in an isolated context for each test.

    Function scope guarantees that cookies, localStorage, and intercepted
    routes from one test cannot bleed into another.
    """
    context = browser_instance.new_context()
    page = context.new_page()
    yield page
    context.close()


# ---------------------------------------------------------------------------
# API data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def api_headers():
    """Build request headers for direct API calls.

    Includes the x-api-key header when REQRES_API_KEY is set in the
    environment, so the same fixture works in both local and CI runs.
    """
    headers: dict[str, str] = {}
    if REQRES_API_KEY:
        headers["x-api-key"] = REQRES_API_KEY
    return headers


@pytest.fixture(scope="session")
def valid_user_list_response() -> dict:
    """Return a fully-valid mocked /api/users?page=2 payload.

    Using a fixture (rather than a module-level constant) means tests can
    receive it via dependency injection and future tests can override it
    with indirect parametrize if needed.
    """
    return {
        "page": 2,
        "per_page": 6,
        "total": 12,
        "total_pages": 2,
        "data": [
            {
                "id": 7,
                "email": "michael.lawson@reqres.in",
                "first_name": "Michael",
                "last_name": "Lawson",
                "avatar": "https://reqres.in/img/faces/7-image.jpg",
            },
            {
                "id": 8,
                "email": "lindsay.ferguson@reqres.in",
                "first_name": "Lindsay",
                "last_name": "Ferguson",
                "avatar": "https://reqres.in/img/faces/8-image.jpg",
            },
        ],
    }


@pytest.fixture(scope="session")
def invalid_schema_cases() -> list[tuple[str, dict]]:
    """Return parametrize-ready pairs of (label, bad_payload).

    Each entry describes one way the API could violate the contract,
    paired with a human-readable label that appears in the test ID.
    """
    return [
        (
            "data_is_string_not_list",
            {"page": 1, "per_page": 6, "total": 1, "total_pages": 1,
             "data": "WRONG_TYPE"},
        ),
        (
            "missing_required_top_level_fields",
            {"data": []},
        ),
        (
            "user_has_invalid_email",
            {
                "page": 1, "per_page": 1, "total": 1, "total_pages": 1,
                "data": [{"id": 1, "email": "not-an-email",
                          "first_name": "A", "last_name": "B",
                          "avatar": "https://example.com/img.jpg"}],
            },
        ),
        (
            "user_id_is_negative",
            {
                "page": 1, "per_page": 1, "total": 1, "total_pages": 1,
                "data": [{"id": -1, "email": "a@b.com",
                          "first_name": "A", "last_name": "B",
                          "avatar": "https://example.com/img.jpg"}],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Global failure hook
# ---------------------------------------------------------------------------

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Enrich failure output based on the exception type.

    Two strategies:
    1. Pydantic ValidationError  → print the structured JSON so the exact
       field path and error type are immediately visible.
    2. Any failure in a UI test  → capture a screenshot next to the test run
       so the visual state at the time of failure is preserved.
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # --- Contract violation ---
        if call.excinfo and isinstance(call.excinfo.value, ValidationError):
            print("\n" + "!" * 50)
            print("CONTRACT ERROR: API response does not match the schema!")
            print(call.excinfo.value.json(indent=2))
            print("!" * 50)

        # --- UI failure screenshot ---
        if "authenticated_page" in item.funcargs:
            page = item.funcargs["authenticated_page"]
            screenshot_path = f"failure_{item.name}.png"
            page.screenshot(path=screenshot_path)
            print(f"\nScreenshot saved: {screenshot_path}")
