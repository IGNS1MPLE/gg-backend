from sqlalchemy.orm import Session
from sqlalchemy import func
import models, schemas
from datetime import date

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Product).offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def get_seller(db: Session, seller_id: int):
    return db.query(models.Seller).filter(models.Seller.id == seller_id).first()

def get_sellers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Seller).offset(skip).limit(limit).all()

def create_seller(db: Session, seller: schemas.SellerCreate):
    db_seller = models.Seller(**seller.model_dump())
    db.add(db_seller)
    db.commit()
    db.refresh(db_seller)
    return db_seller

def dispatch_product(db: Session, log: schemas.DailyLogCreate):
    # Check if a log already exists for this seller, product, and date
    existing_log = db.query(models.DailyLog).filter(
        models.DailyLog.date == log.date,
        models.DailyLog.seller_id == log.seller_id,
        models.DailyLog.product_id == log.product_id
    ).first()

    if existing_log:
        existing_log.dispatched_qty += log.dispatched_qty
        db_log = existing_log
    else:
        db_log = models.DailyLog(**log.model_dump())
        db.add(db_log)
        
    db.commit()
    db.refresh(db_log)
    return db_log

def log_returns(db: Session, log_id: int, returned: schemas.DailyLogReturn):
    db_log = db.query(models.DailyLog).filter(models.DailyLog.id == log_id).first()
    if not db_log:
        return None
        
    db_log.returned_qty = returned.returned_qty
    db_log.sold_qty = db_log.dispatched_qty - db_log.returned_qty
    
    # Financial calculations
    product = get_product(db, db_log.product_id)
    if product:
        db_log.gross_revenue = db_log.sold_qty * product.selling_price
        db_log.seller_payout = db_log.sold_qty * product.commission_rate
        cogs = db_log.sold_qty * product.base_cost
        db_log.net_profit = db_log.gross_revenue - (cogs + db_log.seller_payout)
        
    db.commit()
    db.refresh(db_log)
    return db_log

def get_daily_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DailyLog).offset(skip).limit(limit).all()

# --- Analytics Methods ---

def get_top_products(db: Session, target_month: int, target_year: int, metric: str = 'revenue', limit: int = 10):
    query = db.query(
        models.Product.id,
        models.Product.name,
        func.sum(models.DailyLog.gross_revenue).label("total_revenue"),
        func.sum(models.DailyLog.net_profit).label("total_net_profit"),
        func.sum(models.DailyLog.seller_payout + (models.DailyLog.sold_qty * models.Product.base_cost)).label("total_deductions")
    ).join(models.DailyLog).filter(
        func.extract('month', models.DailyLog.date) == target_month,
        func.extract('year', models.DailyLog.date) == target_year
    ).group_by(models.Product.id)

    if metric == 'revenue':
        query = query.order_by(func.sum(models.DailyLog.gross_revenue).desc())
    else:
        query = query.order_by(func.sum(models.DailyLog.net_profit).desc())
        
    results = query.limit(limit).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "total_revenue": r.total_revenue,
            "total_net_profit": r.total_net_profit,
            "total_deductions": r.total_deductions
        }
        for r in results
    ]

def get_top_sellers(db: Session, target_month: int, target_year: int, metric: str = 'revenue', limit: int = 10):
    query = db.query(
        models.Seller.id,
        models.Seller.name,
        func.sum(models.DailyLog.gross_revenue).label("total_revenue"),
        func.sum(models.DailyLog.net_profit).label("total_net_profit")
    ).join(models.DailyLog).filter(
        func.extract('month', models.DailyLog.date) == target_month,
        func.extract('year', models.DailyLog.date) == target_year
    ).group_by(models.Seller.id)

    if metric == 'revenue':
        query = query.order_by(func.sum(models.DailyLog.gross_revenue).desc())
    else:
        query = query.order_by(func.sum(models.DailyLog.net_profit).desc())
        
    results = query.limit(limit).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "total_revenue": r.total_revenue,
            "total_net_profit": r.total_net_profit
        }
        for r in results
    ]
