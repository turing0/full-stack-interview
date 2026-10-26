from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional

class OptionValueSchema(BaseModel):
    id: int
    value: str
    model_config = ConfigDict(from_attributes=True)


class OptionDimensionSchema(BaseModel):
    id: int
    name: str
    values: List[OptionValueSchema] = []
    model_config = ConfigDict(from_attributes=True)


class SKUSchema(BaseModel):
    id: int
    price: float
    available_quantity: int
    image: Optional[str] = None
    is_available: bool
    option_value_ids: List[int] = []

    model_config = ConfigDict(from_attributes=True)

class ProductDetailSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    dimensions: List[OptionDimensionSchema] = []
    skus: List[SKUSchema] = []
    model_config = ConfigDict(from_attributes=True)

class AddCartItemSchema(BaseModel):
    sku_id: int
    quantity: int = Field(gt=0)

class CartItemResponseSchema(BaseModel):
    id: int
    sku_id: int
    quantity: int
    sku: SKUSchema
    model_config = ConfigDict(from_attributes=True)


class CartResponseSchema(BaseModel):
    id: int
    items: List[CartItemResponseSchema] = []
    total_item_count: int
    model_config = ConfigDict(from_attributes=True)
