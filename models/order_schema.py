"""Pydantic model for the order resource.

Defines the minimum fields an order response must contain.
PositiveInt on 'id' ensures the API never returns 0 or a negative sentinel.
"""

from pydantic import BaseModel, PositiveInt


class OrderSchema(BaseModel):
    """Contract for a single order object returned by the orders API."""

    id: PositiveInt   # Must be a positive integer; rejects 0 and negatives
    status: str
    total_price: float
