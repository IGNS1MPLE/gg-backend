from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

# --- Product Schemas ---
class ProductBase(BaseModel):
    name: str
    category: Optional[str] = "General"
    unit: Optional[str] = "Pcs"
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
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Hawker Schemas ---
class HawkerBase(BaseModel):
    name: str
    contact_info: Optional[str] = None
    route: Optional[str] = ""
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
    route: Optional[str] = ""

class DailyLogCreate(DailyLogBase):
    pass

class DailyLogReturn(BaseModel):
    returned_qty: int
    damaged_qty: Optional[int] = 0
    remarks: Optional[str] = ""
    cash_collected: float

class DailyLog(DailyLogBase):
    id: int
    returned_qty: int
    damaged_qty: Optional[int] = 0
    remarks: Optional[str] = ""
    sold_qty: int
    gross_revenue: float
    hawker_payout: float
    net_profit: float
    cash_collected: float
    outstanding_amount: float

    class Config:
        from_attributes = True

# --- Supplier Schemas ---
class SupplierBase(BaseModel):
    name: str
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class Supplier(SupplierBase):
    id: int

    class Config:
        from_attributes = True

# --- Purchase Schemas ---
class PurchaseBase(BaseModel):
    date: date
    product_id: int
    quantity: int
    total_cost: float
    supplier: Optional[str] = None
    supplier_id: Optional[int] = None
    expiry_date: Optional[date] = None
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

# --- Product Request Schemas ---
class ProductRequestBase(BaseModel):
    requested_date: Optional[date] = None
    hawker_id: Optional[int] = None
    product_name: str
    category: Optional[str] = "General"
    status: Optional[str] = "Pending"
    notes: Optional[str] = None

class ProductRequestCreate(ProductRequestBase):
    pass

class ProductRequest(ProductRequestBase):
    id: int

    class Config:
        from_attributes = True

# --- Category Schemas ---
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    color_code: Optional[str] = "#3b82f6"

class CategoryCreate(CategoryBase):
    pass

class Category(CategoryBase):
    id: int

    class Config:
        from_attributes = True

# --- Product Unit Schemas ---
class ProductUnitBase(BaseModel):
    name: str
    abbreviation: Optional[str] = None
    description: Optional[str] = None

class ProductUnitCreate(ProductUnitBase):
    pass

class ProductUnit(ProductUnitBase):
    id: int

    class Config:
        from_attributes = True

# --- UserAccount Schemas ---
class UserAccountBase(BaseModel):
    name: str
    email: str
    password: Optional[str] = "admin123"
    role: Optional[str] = "Store Manager"
    status: Optional[bool] = True
    notes: Optional[str] = None

class UserAccountCreate(UserAccountBase):
    pass

class UserAccount(UserAccountBase):
    id: int

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    username: str
    password: str
    mode: Optional[str] = "admin" # admin or user

class LoginResponse(BaseModel):
    ok: bool
    user: Optional[UserAccount] = None
    role: str
    message: str
