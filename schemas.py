from pydantic import BaseModel
from typing import Optional, List
from datetime import date

# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str
    category: Optional[str] = "General"
    barcode: Optional[str] = None
    base_cost: float
    selling_price: float
    commission_rate: float
    current_stock: Optional[int] = 0
    min_stock_alert: Optional[int] = 10
    expiry_date: Optional[date] = None

class ProductCreate(ProductBase):
    pass

class Product(ProductBase):
    id: int

    class Config:
        from_attributes = True

# --- Hawker Schemas ---
class HawkerBase(BaseModel):
    name: str
    contact_info: Optional[str] = None
    status: Optional[bool] = True
    balance: Optional[float] = 0.0

class HawkerCreate(HawkerBase):
    pass

class Hawker(HawkerBase):
    id: int

    class Config:
        from_attributes = True

# --- DailyLog Schemas ---
class DailyLogBase(BaseModel):
    date: date
    hawker_id: int
    product_id: int
    dispatched_qty: int

class DailyLogCreate(DailyLogBase):
    pass

class DailyLogReturn(BaseModel):
    returned_qty: int
    cash_collected: float

class DailyLog(DailyLogBase):
    id: int
    returned_qty: int
    sold_qty: int
    gross_revenue: float
    hawker_payout: float
    net_profit: float
    cash_collected: float
    outstanding_amount: float

    class Config:
        from_attributes = True

# --- Purchase Schemas ---
class PurchaseBase(BaseModel):
    date: date
    product_id: int
    quantity: int
    total_cost: float
    supplier: Optional[str] = None
    notes: Optional[str] = None

class PurchaseCreate(PurchaseBase):
    pass

class Purchase(PurchaseBase):
    id: int

    class Config:
        from_attributes = True

# --- Expense Schemas ---
class ExpenseBase(BaseModel):
    date: date
    category: str
    amount: float
    description: Optional[str] = None

class ExpenseCreate(ExpenseBase):
    pass

class Expense(ExpenseBase):
    id: int

    class Config:
        from_attributes = True

# --- Collection Schemas ---
class CollectionBase(BaseModel):
    date: date
    hawker_id: int
    amount: float
    payment_method: Optional[str] = "Cash"

class CollectionCreate(CollectionBase):
    pass

class Collection(CollectionBase):
    id: int

    class Config:
        from_attributes = True
