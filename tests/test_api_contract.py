import pytest
from pydantic import BaseModel, EmailStr, HttpUrl, ValidationError
from playwright.sync_api import APIRequestContext

# 1. THE CONTRACT (The "Senior" part)
# We define exactly what the API should return. 
# If 'email' isn't a real email format, or 'avatar' isn't a URL, it fails.
class UserData(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    avatar: HttpUrl

class ListUsersResponse(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    data: list[UserData]  # Nested list validation

# 2. THE TEST
def test_user_list_schema_validation(authenticated_page):
    """
    Cleaner version: If UserSchema fails, the global hook 
    in conftest.py catches the ValidationError and logs it.
    """
    response = authenticated_page.request.get("https://reqres.in/api/users?page=2")
    assert response.ok
    
    # We simply try to instantiate the model. 
    # If it fails, our global hook handles the custom reporting.
    raw_data = response.json()
    validated_data = ListUsersResponse(**raw_data)
    
    assert validated_data.page == 2
    assert len(validated_data.data) > 0

def test_ui_resilience_to_api_failure(authenticated_page):
    """
    This test will fail intentionally to show off the global hook's 
    ability to catch the Pydantic error and print the details.
    """
    authenticated_page.route("**/api/users**", lambda route: route.fulfill(
        status=200,
        content_type="application/json",
        body='{"data": "WRONG_DATA_TYPE_OBJECT_INSTEAD_OF_LIST"}'
    ))
    
    response = authenticated_page.request.get("https://reqres.in/api/users?page=2")
    # This line will trigger the ValidationError & the Global Hook
    ListUsersResponse(**response.json()) 