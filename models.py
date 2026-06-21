from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    base_cost = Column(Float)
    selling_price = Column(Float)
    commission_rate = Column(Float)  # e.g., 2.5 per unit, or percentage. Let's use fixed amount per unit

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    contact_info = Column(String)

class DailyLog(Base):
    __tablename__ = "daily_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    dispatched_qty = Column(Integer, default=0)
    returned_qty = Column(Integer, default=0)
    
    # Computed fields, but we store them for historical integrity
    sold_qty = Column(Integer, default=0)
    gross_revenue = Column(Float, default=0.0)
    seller_payout = Column(Float, default=0.0)
    net_profit = Column(Float, default=0.0)

    seller = relationship("Seller")
    product = relationship("Product")
