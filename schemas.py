from pydantic import BaseModel
from typing import Optional
from datetime import date

# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str
    base_cost: float
    selling_price: float
    commission_rate: float

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True

# --- Seller Schemas ---
class SellerBase(BaseModel):
    name: str
    contact_info: Optional[str] = None

class SellerCreate(SellerBase):
    pass

class Seller(SellerBase):
    id: int

    class Config:
        from_attributes = True

# --- DailyLog Schemas ---
class DailyLogBase(BaseModel):
    date: date
    seller_id: int
    product_id: int
    dispatched_qty: int

class DailyLogCreate(DailyLogBase):
    pass

class DailyLogReturn(BaseModel):
    returned_qty: int

class DailyLog(DailyLogBase):
    id: int
    returned_qty: int
    sold_qty: int
    gross_revenue: float
    seller_payout: float
    net_profit: float

    class Config:
        from_attributes = True
