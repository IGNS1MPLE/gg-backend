from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True, default="General")
    barcode = Column(String, index=True, nullable=True)
    base_cost = Column(Float, default=0.0)
    selling_price = Column(Float, default=0.0)
    commission_rate = Column(Float, default=0.0)
    
    # Inventory
    current_stock = Column(Integer, default=0)
    min_stock_alert = Column(Integer, default=10)
    expiry_date = Column(Date, nullable=True)

class Hawker(Base):
    __tablename__ = "hawkers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact_info = Column(String, nullable=True)
    status = Column(Boolean, default=True) # Active or Inactive
    balance = Column(Float, default=0.0) # Outstanding balance (negative means they owe us, positive means we owe them or they have credit)

class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, default=datetime.date.today)
    hawker_id = Column(Integer, ForeignKey("hawkers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    dispatched_qty = Column(Integer, default=0)
    returned_qty = Column(Integer, default=0)
    
    sold_qty = Column(Integer, default=0)
    gross_revenue = Column(Float, default=0.0)
    hawker_payout = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)
    
    cash_collected = Column(Float, default=0.0)
    outstanding_amount = Column(Float, default=0.0)

    hawker = relationship("Hawker")
    product = relationship("Product")

class Purchase(Base):
    __tablename__ = "purchases"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today)
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    supplier = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    
    product = relationship("Product")

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today)
    category = Column(String, index=True)
    amount = Column(Float, default=0.0)
    description = Column(String, nullable=True)

class Collection(Base):
    __tablename__ = "collections"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, default=datetime.date.today)
    hawker_id = Column(Integer, ForeignKey("hawkers.id"))
    amount = Column(Float, default=0.0)
    payment_method = Column(String, default="Cash")
    
    hawker = relationship("Hawker")
