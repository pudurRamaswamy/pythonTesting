from pydantic import BaseModel, PositiveInt

class OrderSchema(BaseModel):
    id: PositiveInt
    status: str
    total_price: float