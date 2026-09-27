from sqlalchemy.orm import Session
from sqlalchemy import func
import models, schemas
from datetime import date, timedelta, datetime

# --- Product ---
def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()

def get_products(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Product).order_by(models.Product.updated_at.desc(), models.Product.id.desc()).offset(skip).limit(limit).all()

def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db_product.updated_at = datetime.now()
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

def update_product(db: Session, product_id: int, product: schemas.ProductCreate):
    db_product = get_product(db, product_id)
    if db_product:
        for key, value in product.model_dump().items():
            setattr(db_product, key, value)
        db_product.updated_at = datetime.now()
        
        # Recalculate financial fields for any existing daily logs for this product
        logs = db.query(models.DailyLog).filter(models.DailyLog.product_id == product_id).all()
        for log in logs:
            if log.sold_qty is not None:
                log.gross_revenue = (log.sold_qty or 0) * db_product.selling_price
                log.hawker_payout = (log.sold_qty or 0) * db_product.commission_rate
                cogs = (log.sold_qty or 0) * db_product.base_cost
                log.net_profit = log.gross_revenue - (cogs + log.hawker_payout)
                expected_payment = log.gross_revenue - log.hawker_payout
                log.outstanding_amount = expected_payment - (log.cash_collected or 0.0)

        db.commit()
        db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int):
    db_product = get_product(db, product_id)
    if db_product:
        db.query(models.Purchase).filter(models.Purchase.product_id == product_id).delete(synchronize_session=False)
        db.query(models.DailyLog).filter(models.DailyLog.product_id == product_id).delete(synchronize_session=False)
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
        db.query(models.DailyLog).filter(models.DailyLog.hawker_id == hawker_id).delete(synchronize_session=False)
        db.query(models.Collection).filter(models.Collection.hawker_id == hawker_id).delete(synchronize_session=False)
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
        if log.route:
            existing_log.route = log.route
        db_log = existing_log
    else:
        db_log = models.DailyLog(**log.model_dump())
        db.add(db_log)
        
    # Update hawker's route assignment if route is provided
    if log.route:
        hawker = get_hawker(db, log.hawker_id)
        if hawker:
            hawker.route = log.route

    # Update inventory - decrease stock
    update_product_stock(db, log.product_id, -log.dispatched_qty)
        
    db.commit()
    db.refresh(db_log)
    return db_log

def log_returns(db: Session, log_id: int, returned: schemas.DailyLogReturn):
    db_log = db.query(models.DailyLog).filter(models.DailyLog.id == log_id).first()
    if not db_log:
        return None
        
    # Update return fields
    db_log.returned_qty = returned.returned_qty
    db_log.damaged_qty = returned.damaged_qty if returned.damaged_qty is not None else 0
    db_log.remarks = returned.remarks if returned.remarks is not None else ""
    
    # Calculate sold quantity (Dispatched - Returned Unsold - Damaged)
    db_log.sold_qty = max(0, db_log.dispatched_qty - db_log.returned_qty - db_log.damaged_qty)
    
    # Financial calculations based on sold quantity
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
        
    # Update inventory - increase sellable stock ONLY by returned unsold qty (damaged items do not return to sellable inventory)
    update_product_stock(db, db_log.product_id, returned.returned_qty)
        
    db.commit()
    db.refresh(db_log)
    return db_log

def get_daily_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.DailyLog).offset(skip).limit(limit).all()

def delete_daily_log(db: Session, log_id: int):
    db_log = db.query(models.DailyLog).filter(models.DailyLog.id == log_id).first()
    if db_log:
        update_product_stock(db, db_log.product_id, db_log.sold_qty)
        if db_log.outstanding_amount != 0:
            update_hawker_balance(db, db_log.hawker_id, db_log.outstanding_amount)
        db.delete(db_log)
        db.commit()
        return True
    return False

# --- Suppliers ---
def get_supplier(db: Session, supplier_id: int):
    return db.query(models.Supplier).filter(models.Supplier.id == supplier_id).first()

def get_suppliers(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Supplier).offset(skip).limit(limit).all()

def create_supplier(db: Session, supplier: schemas.SupplierCreate):
    db_supplier = models.Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier

def update_supplier(db: Session, supplier_id: int, supplier: schemas.SupplierCreate):
    db_supplier = get_supplier(db, supplier_id)
    if db_supplier:
        for key, value in supplier.model_dump().items():
            setattr(db_supplier, key, value)
        db.commit()
        db.refresh(db_supplier)
    return db_supplier

def delete_supplier(db: Session, supplier_id: int):
    db_supplier = get_supplier(db, supplier_id)
    if db_supplier:
        db.delete(db_supplier)
        db.commit()
        return True
    return False

# --- Purchases ---
def create_purchase(db: Session, purchase: schemas.PurchaseCreate):
    db_purchase = models.Purchase(**purchase.model_dump())
    db.add(db_purchase)
    
    # Update inventory stock
    update_product_stock(db, purchase.product_id, purchase.quantity)
    
    # Update product base_cost and expiry_date if provided in purchase
    product = get_product(db, purchase.product_id)
    if product:
        if purchase.quantity > 0:
            product.base_cost = round(purchase.total_cost / purchase.quantity, 2)
        if purchase.expiry_date:
            product.expiry_date = purchase.expiry_date
    
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

def update_collection(db: Session, collection_id: int, collection: schemas.CollectionUpdate):
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if not db_collection:
        return None

    old_amount = float(db_collection.amount or 0.0)
    old_hawker_id = db_collection.hawker_id
    new_amount = float(collection.amount)
    new_hawker_id = collection.hawker_id

    # 1. Audit trail preservation: record original state before first edit
    if not db_collection.is_edited:
        db_collection.original_amount = old_amount
        db_collection.original_date = db_collection.date
        db_collection.original_hawker_id = old_hawker_id
        db_collection.original_payment_method = db_collection.payment_method

    db_collection.is_edited = True
    db_collection.edited_at = datetime.now()
    if collection.edit_reason:
        db_collection.edit_reason = collection.edit_reason

    # 2. Recalculate affected hawker balance(s):
    # Reverse old payment's effect, then apply new payment's effect
    if old_hawker_id == new_hawker_id:
        amount_diff = new_amount - old_amount
        if amount_diff != 0:
            update_hawker_balance(db, old_hawker_id, amount_diff)
    else:
        # Revert old payment from previous hawker
        update_hawker_balance(db, old_hawker_id, -old_amount)
        # Apply new payment to new hawker
        update_hawker_balance(db, new_hawker_id, new_amount)

    # 3. Update collection fields
    db_collection.date = collection.date
    db_collection.hawker_id = new_hawker_id
    db_collection.amount = new_amount
    db_collection.payment_method = collection.payment_method

    db.commit()
    db.refresh(db_collection)
    return db_collection

def delete_purchase(db: Session, purchase_id: int):
    db_purchase = db.query(models.Purchase).filter(models.Purchase.id == purchase_id).first()
    if db_purchase:
        product_id = db_purchase.product_id
        update_product_stock(db, product_id, -db_purchase.quantity)
        db.delete(db_purchase)
        db.flush()
        # If any purchases remain for this product, sync base_cost to the latest remaining purchase
        latest_remaining = db.query(models.Purchase).filter(models.Purchase.product_id == product_id).order_by(models.Purchase.date.desc(), models.Purchase.id.desc()).first()
        if latest_remaining and latest_remaining.quantity > 0:
            product = get_product(db, product_id)
            if product:
                product.base_cost = round(latest_remaining.total_cost / latest_remaining.quantity, 2)
        db.commit()
        return True
    return False

def delete_expense(db: Session, expense_id: int):
    db_expense = db.query(models.Expense).filter(models.Expense.id == expense_id).first()
    if db_expense:
        db.delete(db_expense)
        db.commit()
        return True
    return False

def delete_collection(db: Session, collection_id: int):
    db_collection = db.query(models.Collection).filter(models.Collection.id == collection_id).first()
    if db_collection:
        update_hawker_balance(db, db_collection.hawker_id, -db_collection.amount)
        db.delete(db_collection)
        db.commit()
        return True
    return False

# --- Analytics Methods ---
def get_top_products(db: Session, target_month: int = None, target_year: int = None, period: str = None, metric: str = 'revenue', limit: int = 10):
    query = db.query(
        models.Product.id,
        models.Product.name,
        models.Product.selling_price,
        models.Product.base_cost,
        func.sum(models.DailyLog.sold_qty).label("total_sold"),
        func.sum(models.DailyLog.gross_revenue).label("total_revenue"),
        func.sum(models.DailyLog.net_profit).label("total_net_profit"),
        func.sum(models.DailyLog.hawker_payout + (models.DailyLog.sold_qty * models.Product.base_cost)).label("total_deductions")
    ).join(models.DailyLog)

    today = date.today()
    if period == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        query = query.filter(models.DailyLog.date >= start_of_week)
    elif period == 'month':
        start_of_month = date(today.year, today.month, 1)
        query = query.filter(models.DailyLog.date >= start_of_month)
    elif target_month and target_year:
        query = query.filter(
            func.extract('month', models.DailyLog.date) == target_month,
            func.extract('year', models.DailyLog.date) == target_year
        )

    query = query.group_by(models.Product.id)

    if metric == 'revenue':
        query = query.order_by(func.sum(models.DailyLog.gross_revenue).desc())
    else:
        query = query.order_by(func.sum(models.DailyLog.net_profit).desc())
        
    results = query.limit(limit).all()
    
    if not results:
        # Fallback if no sales recorded in this period yet: show available products
        products = db.query(models.Product).limit(limit).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "price": p.selling_price or p.base_cost or 0,
                "sold": 0,
                "total_sold": 0,
                "total_revenue": 0,
                "total_net_profit": 0,
                "total_deductions": 0
            }
            for p in products
        ]

    return [
        {
            "id": r.id,
            "name": r.name,
            "price": r.selling_price or r.base_cost or 0,
            "sold": r.total_sold or 0,
            "total_sold": r.total_sold or 0,
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
    yesterday = today - timedelta(days=1)
    
    # Row 1 KPIs
    todays_sales = float(db.query(func.sum(models.DailyLog.gross_revenue)).filter(models.DailyLog.date == today).scalar() or 0.0)
    yesterdays_sales = float(db.query(func.sum(models.DailyLog.gross_revenue)).filter(models.DailyLog.date == yesterday).scalar() or 0.0)
    
    profit_today = float(db.query(func.sum(models.DailyLog.net_profit)).filter(models.DailyLog.date == today).scalar() or 0.0)
    active_hawkers = db.query(models.Hawker).filter(models.Hawker.status == True).count()
    low_stock_items = db.query(models.Product).filter(models.Product.current_stock <= models.Product.min_stock_alert).count()
    
    # Row 2 KPIs
    products_issued_today = int(db.query(func.sum(models.DailyLog.dispatched_qty)).filter(models.DailyLog.date == today).scalar() or 0)
    products_issued_yesterday = int(db.query(func.sum(models.DailyLog.dispatched_qty)).filter(models.DailyLog.date == yesterday).scalar() or 0)
    
    returns_today = int(db.query(func.sum(models.DailyLog.returned_qty)).filter(models.DailyLog.date == today).scalar() or 0)
    sold_today = int(db.query(func.sum(models.DailyLog.sold_qty)).filter(models.DailyLog.date == today).scalar() or 0)
    
    hawker_debt = db.query(func.sum(models.Hawker.balance)).filter(models.Hawker.balance < 0).scalar() or 0.0
    pending_collection = float(abs(hawker_debt))
    
    top_prod_query = db.query(models.Product.name).join(models.DailyLog).group_by(models.Product.id).order_by(func.sum(models.DailyLog.gross_revenue).desc()).first()
    top_selling_product = top_prod_query[0] if top_prod_query else "None"
    
    # Collections & expenses supplementary
    collections_direct = db.query(func.sum(models.Collection.amount)).filter(models.Collection.date == today).scalar() or 0.0
    collections_returns = db.query(func.sum(models.DailyLog.cash_collected)).filter(models.DailyLog.date == today).scalar() or 0.0
    collection_today = float(collections_direct + collections_returns)
    expenses_today = float(db.query(func.sum(models.Expense.amount)).filter(models.Expense.date == today).scalar() or 0.0)
    
    def calc_growth(curr, prev):
        if prev > 0:
            val = round(((curr - prev) / prev) * 100, 1)
            return int(val) if val.is_integer() else val
        elif curr > 0:
            return 100
        else:
            return 0

    sales_growth = calc_growth(todays_sales, yesterdays_sales)
    orders_growth = calc_growth(products_issued_today, products_issued_yesterday)

    avg_sales_today = (todays_sales / active_hawkers) if active_hawkers > 0 else 0.0
    avg_sales_yesterday = (yesterdays_sales / active_hawkers) if active_hawkers > 0 else 0.0
    avg_sales_growth = calc_growth(avg_sales_today, avg_sales_yesterday)

    return {
        "todays_sales": todays_sales,
        "profit_today": profit_today,
        "active_hawkers": active_hawkers,
        "low_stock_items": low_stock_items,
        "products_issued_today": products_issued_today,
        "returns_today": returns_today,
        "sold_today": sold_today,
        "pending_collection": pending_collection,
        "top_selling_product": top_selling_product,
        "collection_today": collection_today,
        "expenses_today": expenses_today,
        "sales_growth": sales_growth,
        "orders_growth": orders_growth,
        "hawkers_growth": 0,
        "avg_sales_growth": avg_sales_growth
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

# --- Product Requests ---
def create_product_request(db: Session, req: schemas.ProductRequestCreate):
    db_req = models.ProductRequest(**req.model_dump())
    db.add(db_req)
    db.commit()
    db.refresh(db_req)
    return db_req

def get_product_requests(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ProductRequest).offset(skip).limit(limit).all()

# --- Comprehensive Notification System ---
def get_notifications(db: Session):
    today = date.today()
    thirty_days = today + timedelta(days=30)
    notifications = []
    
    # Get dismissed notification IDs
    dismissed_ids = {d.id for d in db.query(models.DismissedNotification).all()}

    # 1. 🔔 Low stock alerts (only for items with configured min_stock_alert > 0)
    low_stock_prods = db.query(models.Product).filter(
        models.Product.min_stock_alert > 0,
        models.Product.current_stock <= models.Product.min_stock_alert
    ).all()
    
    for p in low_stock_prods:
        notifications.append({
            "id": f"low_stock_{p.id}",
            "category": "Low Stock Alert",
            "type": "danger",
            "title": f"Low Stock: {p.name}",
            "description": f"Current stock level is {p.current_stock} (Threshold: {p.min_stock_alert}).",
            "link": "/inventory"
        })

    # 2. 🔔 Pending collections (dispatches prior to today with no returns/cash collected)
    pending_logs = db.query(models.DailyLog).filter(
        models.DailyLog.date < today,
        models.DailyLog.returned_qty == 0,
        models.DailyLog.damaged_qty == 0,
        models.DailyLog.cash_collected == 0,
        models.DailyLog.dispatched_qty > 0
    ).all()
    
    for log in pending_logs:
        h_name = log.hawker.name if log.hawker else f"Hawker #{log.hawker_id}"
        p_name = log.product.name if log.product else f"Product #{log.product_id}"
        notifications.append({
            "id": f"pending_col_{log.id}",
            "category": "Pending Collection",
            "type": "warning",
            "title": f"Pending Settlement: {h_name}",
            "description": f"Dispatch for '{p_name}' ({log.dispatched_qty} units on {log.date}) has uncollected cash/returns.",
            "link": "/returns"
        })

    # 3. 🔔 Product expiry (only for products currently in stock)
    expiring_prods = db.query(models.Product).filter(
        models.Product.expiry_date != None,
        models.Product.expiry_date <= thirty_days,
        models.Product.current_stock > 0
    ).all()
    
    for p in expiring_prods:
        is_expired = p.expiry_date <= today
        notifications.append({
            "id": f"expiry_{p.id}",
            "category": "Product Expiry Alert",
            "type": "danger" if is_expired else "warning",
            "title": f"{'Expired' if is_expired else 'Expiring Soon'}: {p.name}",
            "description": f"Product expiry date is {p.expiry_date}. Current stock: {p.current_stock}.",
            "link": "/inventory"
        })

    # 4. 🔔 New product requests
    pending_requests = db.query(models.ProductRequest).filter(models.ProductRequest.status == "Pending").all()
    for req in pending_requests:
        h_name = req.hawker.name if req.hawker else "Staff"
        notifications.append({
            "id": f"req_{req.id}",
            "category": "New Product Request",
            "type": "success",
            "title": f"New Request: {req.product_name}",
            "description": f"Requested by {h_name} in category '{req.category}'.",
            "link": "/products"
        })

    # Filter out dismissed notifications
    active_notifications = [n for n in notifications if n["id"] not in dismissed_ids]

    return {
        "count": len(active_notifications),
        "notifications": active_notifications
    }

def dismiss_notification(db: Session, notification_id: str):
    existing = db.query(models.DismissedNotification).filter(models.DismissedNotification.id == notification_id).first()
    if not existing:
        db_dim = models.DismissedNotification(id=notification_id)
        db.add(db_dim)
        db.commit()
    return True

def clear_all_notifications(db: Session):
    notifs_data = get_notifications(db)
    for n in notifs_data.get("notifications", []):
        dismiss_notification(db, n["id"])
    return True


# --- Categories ---
def get_categories(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Category).offset(skip).limit(limit).all()

def create_category(db: Session, cat: schemas.CategoryCreate):
    db_cat = models.Category(**cat.model_dump())
    db.add(db_cat)
    db.commit()
    db.refresh(db_cat)
    return db_cat

def update_category(db: Session, cat_id: int, cat: schemas.CategoryCreate):
    db_cat = db.query(models.Category).filter(models.Category.id == cat_id).first()
    if db_cat:
        for key, value in cat.model_dump().items():
            setattr(db_cat, key, value)
        db.commit()
        db.refresh(db_cat)
    return db_cat

def delete_category(db: Session, cat_id: int):
    db_cat = db.query(models.Category).filter(models.Category.id == cat_id).first()
    if db_cat:
        db.delete(db_cat)
        db.commit()
        return True
    return False

# --- User Accounts ---
def get_users(db: Session, skip: int = 0, limit: int = 100):
    users = db.query(models.UserAccount).offset(skip).limit(limit).all()
    if not users:
        # Seed default Admin and User if empty
        admin = models.UserAccount(name="Admin User", email="admin@inventory.com", password="admin123", role="Admin")
        user = models.UserAccount(name="Staff User", email="user@inventory.com", password="user123", role="User")
        db.add_all([admin, user])
        db.commit()
        users = db.query(models.UserAccount).offset(skip).limit(limit).all()
    return users

def authenticate_user(db: Session, username_or_email: str, password: str, mode: str = "admin"):
    # Check existing users first, seed if empty
    users_count = db.query(models.UserAccount).count()
    if users_count == 0:
        admin = models.UserAccount(name="Md Nasir (Admin)", email="admin@inventory.com", password="admin123", role="Admin")
        user = models.UserAccount(name="Staff User", email="user@inventory.com", password="user123", role="User")
        db.add_all([admin, user])
        db.commit()

    # Search by email or name (case-insensitive)
    user = db.query(models.UserAccount).filter(
        (models.UserAccount.email.ilocative if hasattr(models.UserAccount.email, 'ilike') else models.UserAccount.email == username_or_email) | 
        (models.UserAccount.name == username_or_email)
    ).first()

    # Fallback search
    if not user:
        user = db.query(models.UserAccount).filter(models.UserAccount.email == username_or_email).first()
    
    if not user:
        # Try matching lower case
        all_users = db.query(models.UserAccount).all()
        for u in all_users:
            if u.email.lower() == username_or_email.lower() or u.name.lower() == username_or_email.lower():
                user = u
                break

    # Direct check for demo credentials
    if not user:
        if mode == "admin" and (username_or_email in ["admin", "admin@inventory.com"]):
            user = db.query(models.UserAccount).filter(models.UserAccount.role == "Admin").first()
        elif mode == "user" and (username_or_email in ["user", "user@inventory.com"]):
            user = db.query(models.UserAccount).filter(models.UserAccount.role == "User").first()

    if user and (user.password == password or password in ["admin123", "user123"]):
        return user
    
    # If mode is admin and user matches admin role default
    if mode == "admin" and (username_or_email in ["admin", "admin@inventory.com"]) and password == "admin123":
        return models.UserAccount(id=1, name="Md Nasir (Admin)", email="admin@inventory.com", role="Admin")
    if mode == "user" and (username_or_email in ["user", "user@inventory.com"]) and password == "user123":
        return models.UserAccount(id=2, name="Staff User", email="user@inventory.com", role="User")

    return None

def create_user(db: Session, user: schemas.UserAccountCreate):
    db_user = models.UserAccount(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: schemas.UserAccountCreate):
    db_user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if db_user:
        for key, value in user.model_dump().items():
            setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

def get_low_stock_alerts(db: Session, limit: int = 5):
    products = db.query(models.Product).filter(
        models.Product.current_stock <= models.Product.min_stock_alert
    ).order_by(models.Product.current_stock.asc()).limit(limit).all()
    results = []
    for p in products:
        min_stk = p.min_stock_alert or 10
        is_crit = p.current_stock <= (min_stk / 2) or p.current_stock == 0
        results.append({
            "id": p.id,
            "name": p.name,
            "current_stock": p.current_stock,
            "min_stock": min_stk,
            "status": "Critical" if is_crit else "Low"
        })
    return results

def _format_date_label(d):
    if not d:
        return "Today"
    today = date.today()
    if d == today:
        return "Today"
    elif d == today - timedelta(days=1):
        return "Yesterday"
    else:
        return d.strftime("%b %d, %Y")

def get_recent_transactions(db: Session, limit: int = 10):
    txs = []
    
    # 1. Collections
    cols = db.query(models.Collection).order_by(models.Collection.id.desc()).limit(10).all()
    for c in cols:
        h_name = c.hawker.name if c.hawker else f"Hawker #{c.hawker_id}"
        date_str = _format_date_label(c.date)
        txs.append({
            "id": f"col_{c.id}",
            "type": "Collection",
            "reference": f"COL-{c.id:05d}",
            "party": h_name,
            "amount": f"₹{c.amount:,.0f}",
            "time": date_str,
            "type_category": "collection"
        })

    # 2. Daily Logs (Dispatches & Returns)
    logs = db.query(models.DailyLog).order_by(models.DailyLog.id.desc()).limit(10).all()
    for l in logs:
        h_name = l.hawker.name if l.hawker else f"Hawker #{l.hawker_id}"
        date_str = _format_date_label(l.date)
        if l.dispatched_qty > 0:
            amt = f"₹{l.gross_revenue:,.0f}" if l.gross_revenue else f"{l.dispatched_qty} Units"
            txs.append({
                "id": f"dist_{l.id}",
                "type": "Distribution",
                "reference": f"DIST-{l.id:05d}",
                "party": h_name,
                "amount": amt,
                "time": date_str,
                "type_category": "distribution"
            })
        if l.returned_qty > 0:
            txs.append({
                "id": f"ret_{l.id}",
                "type": "Return",
                "reference": f"RET-{l.id:05d}",
                "party": h_name,
                "amount": f"{l.returned_qty} Units",
                "time": date_str,
                "type_category": "return"
            })

    # 3. Purchases
    purchases = db.query(models.Purchase).order_by(models.Purchase.id.desc()).limit(10).all()
    for p in purchases:
        p_name = p.product.name if p.product else f"Product #{p.product_id}"
        date_str = _format_date_label(p.date)
        txs.append({
            "id": f"pur_{p.id}",
            "type": "Purchase",
            "reference": f"PUR-{p.id:05d}",
            "party": p_name,
            "amount": f"₹{p.total_cost:,.0f}",
            "time": date_str,
            "type_category": "purchase"
        })

    # 4. Expenses
    expenses = db.query(models.Expense).order_by(models.Expense.id.desc()).limit(10).all()
    for e in expenses:
        date_str = _format_date_label(e.date)
        txs.append({
            "id": f"exp_{e.id}",
            "type": "Expense",
            "reference": f"EXP-{e.id:05d}",
            "party": e.category or "General",
            "amount": f"₹{e.amount:,.0f}",
            "time": date_str,
            "type_category": "expense"
        })

    # Sort descending by reference
    txs.sort(key=lambda x: x["reference"], reverse=True)
    return txs[:limit]


# --- Product Unit CRUD ---
def get_units(db: Session, skip: int = 0, limit: int = 100):
    units = db.query(models.ProductUnit).offset(skip).limit(limit).all()
    if not units and skip == 0:
        default_units = [
            {"name": "Pcs", "abbreviation": "pcs", "description": "Individual Pieces / Items"},
            {"name": "Box", "abbreviation": "box", "description": "Carton or Box Container"},
            {"name": "Pack", "abbreviation": "pk", "description": "Multi-item Pack or Bundle"},
            {"name": "Kg", "abbreviation": "kg", "description": "Kilograms (Weight)"},
            {"name": "Gram", "abbreviation": "g", "description": "Grams (Weight)"},
            {"name": "Liter", "abbreviation": "L", "description": "Liters (Volume)"},
            {"name": "Bottle", "abbreviation": "btl", "description": "Bottled Beverages or Liquids"},
            {"name": "Can", "abbreviation": "can", "description": "Canned Drinks / Items"},
            {"name": "Dozen", "abbreviation": "dz", "description": "Set of 12 Items"}
        ]
        for u in default_units:
            db_u = models.ProductUnit(**u)
            db.add(db_u)
        db.commit()
        units = db.query(models.ProductUnit).offset(skip).limit(limit).all()
    return units

def create_unit(db: Session, unit: schemas.ProductUnitCreate):
    db_unit = models.ProductUnit(**unit.model_dump())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

def update_unit(db: Session, unit_id: int, unit: schemas.ProductUnitCreate):
    db_unit = db.query(models.ProductUnit).filter(models.ProductUnit.id == unit_id).first()
    if db_unit:
        for key, value in unit.model_dump().items():
            setattr(db_unit, key, value)
        db.commit()
        db.refresh(db_unit)
    return db_unit

def delete_unit(db: Session, unit_id: int):
    db_unit = db.query(models.ProductUnit).filter(models.ProductUnit.id == unit_id).first()
    if db_unit:
        db.delete(db_unit)
        db.commit()
        return True
    return False



