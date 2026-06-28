from sqlalchemy.orm import Session
from sqlalchemy import func
import models, schemas
from datetime import date, timedelta

# --- Product ---
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

def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product.model_dump().items():
            setattr(db_product, key, value)
        db.commit()
        db.refresh(db_product)
    return db_product

def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.delete(db_product)
        db.commit()
        return True
    return False

def update_product_stock(db: Session, product_id: int, quantity_change: int):
    product = get_product(db, product_id)
    if product:
        product.current_stock += quantity_change
        db.commit()
        db.refresh(product)
    return product

# --- Hawker ---
def get_hawker(db: Session, hawker_id: int):
    return db.query(models.Hawker).filter(models.Hawker.id == hawker_id).first()

def get_hawkers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Hawker).offset(skip).limit(limit).all()

def create_hawker(db: Session, hawker: schemas.HawkerCreate):
    db_hawker = models.Hawker(**hawker.model_dump())
    db.add(db_hawker)
    db.commit()
    db.refresh(db_hawker)
    return db_hawker

def update_hawker(db: Session, hawker_id: int, hawker: schemas.HawkerCreate):
    db_hawker = get_hawker(db, hawker_id)
    if db_hawker:
        for key, value in hawker.model_dump().items():
            setattr(db_hawker, key, value)
        db.commit()
        db.refresh(db_hawker)
    return db_hawker

def delete_hawker(db: Session, hawker_id: int):
    db_hawker = get_hawker(db, hawker_id)
    if db_hawker:
        db.delete(db_hawker)
        db.commit()
        return True
    return False

def update_hawker_balance(db: Session, hawker_id: int, amount_change: float):
    hawker = get_hawker(db, hawker_id)
    if hawker:
        hawker.balance += amount_change
        db.commit()
        db.refresh(hawker)
    return hawker

# --- Daily Log (Dispatch & Returns) ---
def dispatch_product(db: Session, log: schemas.DailyLogCreate):
    # Check if a log already exists for this hawker, product, and date
    existing_log = db.query(models.DailyLog).filter(
        models.DailyLog.date == log.date,
        models.DailyLog.hawker_id == log.hawker_id,
        models.DailyLog.product_id == log.product_id
    ).first()

    if existing_log:
        existing_log.dispatched_qty += log.dispatched_qty
        db_log = existing_log
    else:
        db_log = models.DailyLog(**log.model_dump())
        db.add(db_log)
        
    # Update inventory - decrease stock
    update_product_stock(db, log.product_id, -log.dispatched_qty)
        
    db.commit()
    db.refresh(db_log)
    return db_log

def log_returns(db: Session, log_id: int, returned: schemas.DailyLogReturn):
    db_log = db.query(models.DailyLog).filter(models.DailyLog.id == log_id).first()
    if not db_log:
        return None
        
    # Revert previous return effects if any (not strictly needed if we assume returns are logged once)
    # Update returned qty
    db_log.returned_qty = returned.returned_qty
    db_log.sold_qty = db_log.dispatched_qty - db_log.returned_qty
    
    # Financial calculations
    product = get_product(db, db_log.product_id)
    if product:
        db_log.gross_revenue = db_log.sold_qty * product.selling_price
        db_log.hawker_payout = db_log.sold_qty * product.commission_rate
        cogs = db_log.sold_qty * product.base_cost
        db_log.net_profit = db_log.gross_revenue - (cogs + db_log.hawker_payout)
        
    db_log.cash_collected = returned.cash_collected
    
    # Calculate outstanding: Hawker should pay (gross - their payout), but they paid cash_collected
    expected_payment = db_log.gross_revenue - db_log.hawker_payout
    db_log.outstanding_amount = expected_payment - db_log.cash_collected
    
    # Update hawker balance (negative means they owe us)
    if db_log.outstanding_amount != 0:
        update_hawker_balance(db, db_log.hawker_id, -db_log.outstanding_amount)
        
    # Update inventory - increase stock by returned qty
    update_product_stock(db, db_log.product_id, returned.returned_qty)
        
    db.commit()
    db.refresh(db_log)
    return db_log

def get_daily_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DailyLog).offset(skip).limit(limit).all()

# --- Purchases ---
def create_purchase(db: Session, purchase: schemas.PurchaseCreate):
    db_purchase = models.Purchase(**purchase.model_dump())
    db.add(db_purchase)
    
    # Update inventory
    update_product_stock(db, purchase.product_id, purchase.quantity)
    
    db.commit()
    db.refresh(db_purchase)
    return db_purchase

def get_purchases(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Purchase).offset(skip).limit(limit).all()

# --- Expenses ---
def create_expense(db: Session, expense: schemas.ExpenseCreate):
    db_expense = models.Expense(**expense.model_dump())
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

def get_expenses(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Expense).offset(skip).limit(limit).all()

# --- Collections ---
def create_collection(db: Session, collection: schemas.CollectionCreate):
    db_collection = models.Collection(**collection.model_dump())
    db.add(db_collection)
    
    # Hawker paid money, balance increases (reduces their debt)
    update_hawker_balance(db, collection.hawker_id, collection.amount)
    
    db.commit()
    db.refresh(db_collection)
    return db_collection

def get_collections(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Collection).offset(skip).limit(limit).all()

# --- Analytics Methods ---
def get_top_products(db: Session, target_month: int, target_year: int, metric: str = 'revenue', limit: int = 10):
    query = db.query(
        models.Product.id,
        models.Product.name,
        func.sum(models.DailyLog.gross_revenue).label("total_revenue"),
        func.sum(models.DailyLog.net_profit).label("total_net_profit"),
        func.sum(models.DailyLog.hawker_payout + (models.DailyLog.sold_qty * models.Product.base_cost)).label("total_deductions")
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
            "total_revenue": r.total_revenue or 0,
            "total_net_profit": r.total_net_profit or 0,
            "total_deductions": r.total_deductions or 0
        }
        for r in results
    ]

def get_top_hawkers(db: Session, target_month: int, target_year: int, metric: str = 'revenue', limit: int = 10):
    query = db.query(
        models.Hawker.id,
        models.Hawker.name,
        func.sum(models.DailyLog.gross_revenue).label("total_revenue"),
        func.sum(models.DailyLog.net_profit).label("total_net_profit")
    ).join(models.DailyLog).filter(
        func.extract('month', models.DailyLog.date) == target_month,
        func.extract('year', models.DailyLog.date) == target_year
    ).group_by(models.Hawker.id)

    if metric == 'revenue':
        query = query.order_by(func.sum(models.DailyLog.gross_revenue).desc())
    else:
        query = query.order_by(func.sum(models.DailyLog.net_profit).desc())
        
    results = query.limit(limit).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "total_revenue": r.total_revenue or 0,
            "total_net_profit": r.total_net_profit or 0
        }
        for r in results
    ]

def get_dashboard_kpis(db: Session):
    today = date.today()
    
    # Today's Sales
    todays_sales = db.query(func.sum(models.DailyLog.gross_revenue)).filter(models.DailyLog.date == today).scalar() or 0.0
    
    # Active Hawkers count
    active_hawkers = db.query(models.Hawker).filter(models.Hawker.status == True).count()
    
    # Low Stock Items
    low_stock_items = db.query(models.Product).filter(models.Product.current_stock <= models.Product.min_stock_alert).count()
    
    return {
        "todays_sales": todays_sales,
        "active_hawkers": active_hawkers,
        "low_stock_items": low_stock_items
    }

def get_weekly_sales_trend(db: Session):
    today = date.today()
    start_date = today - timedelta(days=6)
    
    daily_sales = db.query(
        models.DailyLog.date,
        func.sum(models.DailyLog.gross_revenue).label("sales")
    ).filter(
        models.DailyLog.date >= start_date,
        models.DailyLog.date <= today
    ).group_by(models.DailyLog.date).order_by(models.DailyLog.date).all()
    
    sales_dict = {log.date: (log.sales or 0) for log in daily_sales}
    
    trend = []
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        day_name = current_date.strftime("%a") # e.g., Mon, Tue
        trend.append({
            "name": day_name,
            "sales": float(sales_dict.get(current_date, 0))
        })
        
    return trend

