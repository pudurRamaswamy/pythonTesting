"""API contract tests for the reqres.in /users endpoints.

Architecture
============
Three layers are kept deliberately separate:

1. Schema layer  (models/user_schema.py)
   Pydantic models declare the exact shape the API must return.
   They are the "contract" — independent of any HTTP library.

2. Transport layer  (Playwright APIRequestContext via conftest fixtures)
   Responsible only for making the HTTP call and returning raw JSON.
   In most tests below this is replaced by a mock so tests are hermetic.

3. Validation layer  (this file)
   Passes raw JSON into the schema layer and asserts on the typed result.

Test categories (run selectively with -m):
  pytest -m smoke      → fast sanity checks
  pytest -m contract   → schema-shape correctness
  pytest -m negative   → ensure bad payloads are rejected
  pytest -m live       → requires REQRES_API_KEY env var, hits real API
"""

from __future__ import annotations

import json
import os

import pytest
from pydantic import ValidationError

from models.user_schema import ListUsersResponse, SingleUserResponse, UserData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_route(page, body: dict | str):
    """Register a Playwright route that returns *body* for any /api/users* request.

    Using page.route() intercepts requests made via page.goto() and
    page.evaluate() (i.e., JavaScript fetch inside the browser). For
    pure schema tests we inject data directly without HTTP at all.
    """
    if isinstance(body, dict):
        body = json.dumps(body)
    page.route("**/api/users**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body=body,
    ))


# ---------------------------------------------------------------------------
# Smoke tests — basic sanity, always run
# ---------------------------------------------------------------------------

@pytest.mark.smoke
def test_valid_payload_builds_model(valid_user_list_response):
    """Confirm that a well-formed payload round-trips through the schema cleanly.

    No HTTP involved: we pass a pre-built dict straight into the model.
    This is the fastest possible contract check and should always be green.
    """
    result = ListUsersResponse(**valid_user_list_response)

    assert result.page == 2
    assert result.per_page == 6
    assert len(result.data) == 2


@pytest.mark.smoke
def test_user_fields_are_typed_correctly(valid_user_list_response):
    """Verify that Pydantic has coerced / validated individual field types.

    Specifically: email must be a valid EmailStr and avatar must be an HttpUrl.
    These would have raised during construction if the fixture data were wrong.
    """
    result = ListUsersResponse(**valid_user_list_response)
    first: UserData = result.data[0]

    assert "@" in str(first.email)
    assert str(first.avatar).startswith("https://")
    assert first.id > 0


# ---------------------------------------------------------------------------
# Contract tests — exhaustive schema coverage
# ---------------------------------------------------------------------------

@pytest.mark.contract
def test_pagination_fields_are_present(valid_user_list_response):
    """All four pagination envelope fields must be present and non-negative.

    Catching a missing 'total_pages' here prevents downstream callers from
    silently swallowing a KeyError when building pagination UI.
    """
    result = ListUsersResponse(**valid_user_list_response)

    assert result.total >= result.per_page
    assert result.total_pages >= 1


@pytest.mark.contract
def test_single_user_schema(valid_user_list_response):
    """SingleUserResponse wraps one UserData — validate it matches the contract."""
    raw_user = valid_user_list_response["data"][0]
    result = SingleUserResponse(data=raw_user)

    assert result.data.first_name == "Michael"


@pytest.mark.contract
@pytest.mark.parametrize("page_number,expected_users", [
    (1, 2),  # page 1 of our fixture has 2 users
    (2, 2),  # page 2 same count (both point to same fixture data here)
])
def test_paginated_user_count(valid_user_list_response, page_number, expected_users):
    """Schema stays valid regardless of which page the caller requests.

    Parametrize drives the same assertion logic against multiple inputs,
    exposing failures that only appear on specific pages.
    """
    payload = {**valid_user_list_response, "page": page_number}
    result = ListUsersResponse(**payload)

    assert len(result.data) == expected_users


@pytest.mark.contract
def test_mocked_api_response_via_route(authenticated_page, valid_user_list_response):
    """End-to-end path: route mock → page fetch → schema validation.

    Uses Playwright's page.route() to intercept a JavaScript fetch() call
    made from within the browser. This tests the full pipeline — from
    network interception through JSON parsing to Pydantic validation —
    without depending on the live reqres.in service.
    """
    _mock_route(authenticated_page, valid_user_list_response)

    # Execute fetch() inside the browser; route intercepts it and returns mock.
    raw_json = authenticated_page.evaluate(
        "() => fetch('https://reqres.in/api/users?page=2').then(r => r.json())"
    )
    result = ListUsersResponse(**raw_json)

    assert result.page == 2
    assert len(result.data) > 0


# ---------------------------------------------------------------------------
# Negative tests — bad payloads must be rejected
# ---------------------------------------------------------------------------

@pytest.mark.negative
@pytest.mark.parametrize("bad_payload", [
    {"page": 1, "per_page": 6, "total": 1, "total_pages": 1,
     "data": "WRONG_TYPE"},
    {"data": []},
    {
        "page": 1, "per_page": 1, "total": 1, "total_pages": 1,
        "data": [{"id": 1, "email": "not-an-email",
                  "first_name": "A", "last_name": "B",
                  "avatar": "https://example.com/img.jpg"}],
    },
    {
        "page": 1, "per_page": 1, "total": 1, "total_pages": 1,
        "data": [{"id": 1, "email": "a@b.com",
                  "first_name": "A", "last_name": "B",
                  "avatar": "not-a-url"}],
    },
], ids=[
    "data_is_string_not_list",
    "missing_required_top_level_fields",
    "user_has_invalid_email",
    "user_avatar_is_not_a_url",
])
def test_invalid_payloads_raise_validation_error(bad_payload):
    """Every malformed payload must raise ValidationError — never pass silently.

    Parametrize covers multiple failure modes in a single test function:
    - wrong collection type for 'data'
    - entire envelope missing required keys
    - invalid email format inside a user object
    - non-URL string in the avatar field

    The global hook in conftest.py pretty-prints the JSON diff on failure,
    so a real regression here produces immediately actionable output.
    """
    with pytest.raises(ValidationError):
        ListUsersResponse(**bad_payload)


@pytest.mark.negative
def test_mocked_bad_response_rejected_via_route(authenticated_page):
    """Route returns a syntactically valid but schema-invalid JSON body.

    This demonstrates the resilience pattern: even when the network stack
    returns HTTP 200, the contract layer rejects the response if the shape
    is wrong. The global conftest hook will pretty-print the ValidationError.
    """
    bad_body = {"page": 1, "per_page": 1, "total": 1, "total_pages": 1,
                "data": "WRONG_DATA_TYPE_OBJECT_INSTEAD_OF_LIST"}

    _mock_route(authenticated_page, bad_body)

    raw_json = authenticated_page.evaluate(
        "() => fetch('https://reqres.in/api/users?page=2').then(r => r.json())"
    )

    with pytest.raises(ValidationError):
        ListUsersResponse(**raw_json)


# ---------------------------------------------------------------------------
# Live API tests — skipped unless REQRES_API_KEY is set
# ---------------------------------------------------------------------------

@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("REQRES_API_KEY"),
    reason="REQRES_API_KEY not set — skipping live API test",
)
def test_live_user_list_schema_validation(authenticated_page):
    """Hit the real reqres.in endpoint and validate the response shape.

    Requires a free API key from https://app.reqres.in/api-keys set as
    the REQRES_API_KEY environment variable. Skipped in environments
    without the key so CI doesn't hard-fail on a missing secret.
    """
    api_key = os.environ["REQRES_API_KEY"]
    response = authenticated_page.request.get(
        "https://reqres.in/api/users?page=2",
        headers={"x-api-key": api_key},
    )
    assert response.ok, f"Expected 200, got {response.status}"

    result = ListUsersResponse(**response.json())

    assert result.page == 2
    assert len(result.data) > 0
