"""Pydantic models that define the API contract for user-related endpoints.

These schemas serve as the single source of truth for what the reqres.in /users
API is allowed to return. Any drift from this shape is caught at validation time.
"""

from pydantic import BaseModel, EmailStr, HttpUrl


class UserData(BaseModel):
    """Shape of a single user object returned inside the 'data' list."""

    id: int
    email: EmailStr        # Must be a valid RFC-5321 email address
    first_name: str
    last_name: str
    avatar: HttpUrl        # Must be an absolute URL


class ListUsersResponse(BaseModel):
    """Contract for GET /api/users?page=N — a paginated list of users."""

    page: int
    per_page: int
    total: int
    total_pages: int
    data: list[UserData]   # Nested validation: every element must match UserData


class SingleUserResponse(BaseModel):
    """Contract for GET /api/users/{id} — a single user lookup."""

    data: UserData
