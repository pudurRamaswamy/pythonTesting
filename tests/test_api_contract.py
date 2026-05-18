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
    Test Goal: Validate that the 'List Users' API matches our expected schema.
    This catches backend changes before they break the UI.
    """
    # Using Playwright's built-in request context
    api_request: APIRequestContext = authenticated_page.request
    response = api_request.get("https://reqres.in/api/users?page=2")
    
    # Check transport
    assert response.ok, f"API Request failed with status {response.status}"
    
    # VALIDATION LOGIC
    try:
        raw_data = response.json()
        # This line validates the entire nested JSON structure at once
        validated_data = ListUsersResponse(**raw_data)
        
        # Now we have a fully-typed Python object
        print(f"\nSuccessfully validated {len(validated_data.data)} users.")
        assert validated_data.page == 2
        assert "@" in validated_data.data[0].email
        
    except ValidationError as e:
        # If the API developer changed 'id' to a string, Pydantic catches it here.
        pytest.fail(f"API Contract Broken! Schema mismatch: {e.json()}")