from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models, schemas, crud
from database import engine, get_db

from sqlalchemy import text

models.Base.metadata.create_all(bind=engine)

# Auto-migrate SQLite schema for route, damaged_qty, remarks, supplier_id, and expiry_date columns
with engine.connect() as conn:
    for stmt in [
        "ALTER TABLE hawkers ADD COLUMN route VARCHAR DEFAULT ''",
        "ALTER TABLE daily_logs ADD COLUMN route VARCHAR DEFAULT ''",
        "ALTER TABLE daily_logs ADD COLUMN damaged_qty INTEGER DEFAULT 0",
        "ALTER TABLE daily_logs ADD COLUMN remarks VARCHAR DEFAULT ''",
        "ALTER TABLE purchases ADD COLUMN supplier_id INTEGER",
        "ALTER TABLE purchases ADD COLUMN expiry_date DATE",
        "ALTER TABLE products ADD COLUMN unit VARCHAR DEFAULT 'Pcs'",
        "ALTER TABLE products ADD COLUMN updated_at DATETIME",
        "ALTER TABLE collections ADD COLUMN is_edited BOOLEAN DEFAULT 0",
        "ALTER TABLE collections ADD COLUMN edited_at DATETIME",
        "ALTER TABLE collections ADD COLUMN original_amount FLOAT",
        "ALTER TABLE collections ADD COLUMN original_date DATE",
        "ALTER TABLE collections ADD COLUMN original_hawker_id INTEGER",
        "ALTER TABLE collections ADD COLUMN original_payment_method VARCHAR DEFAULT ''",
        "ALTER TABLE collections ADD COLUMN edit_reason VARCHAR DEFAULT ''"
    ]:
        try:
            conn.execute(text(stmt))
            conn.commit()
        except Exception:
            pass

app = FastAPI(title="Consignment & Hawker Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow frontend to access API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Products ---
@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db=db, product=product)

@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_products(db, skip=skip, limit=limit)

@app.put("/products/{product_id}", response_model=schemas.Product)
def update_product(product_id: int, product: schemas.ProductCreate, db: Session = Depends(get_db)):
    updated_product = crud.update_product(db, product_id, product)
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return updated_product

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    success = crud.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"ok": True}

# --- Hawkers ---
@app.post("/hawkers/", response_model=schemas.Hawker)
def create_hawker(hawker: schemas.HawkerCreate, db: Session = Depends(get_db)):
    return crud.create_hawker(db=db, hawker=hawker)

@app.get("/hawkers/", response_model=List[schemas.Hawker])
def read_hawkers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_hawkers(db, skip=skip, limit=limit)

@app.put("/hawkers/{hawker_id}", response_model=schemas.Hawker)
def update_hawker(hawker_id: int, hawker: schemas.HawkerCreate, db: Session = Depends(get_db)):
    updated_hawker = crud.update_hawker(db, hawker_id, hawker)
    if not updated_hawker:
        raise HTTPException(status_code=404, detail="Hawker not found")
    return updated_hawker

@app.delete("/hawkers/{hawker_id}")
def delete_hawker(hawker_id: int, db: Session = Depends(get_db)):
    success = crud.delete_hawker(db, hawker_id)
    if not success:
        raise HTTPException(status_code=404, detail="Hawker not found")
    return {"ok": True}

# --- Daily Logs (Dispatch & Returns) ---
@app.post("/dispatch/", response_model=schemas.DailyLog)
def dispatch_product(log: schemas.DailyLogCreate, db: Session = Depends(get_db)):
    return crud.dispatch_product(db=db, log=log)

@app.get("/logs/", response_model=List[schemas.DailyLog])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_daily_logs(db, skip=skip, limit=limit)

@app.put("/returns/{log_id}", response_model=schemas.DailyLog)
def log_returns(log_id: int, returned: schemas.DailyLogReturn, db: Session = Depends(get_db)):
    db_log = crud.log_returns(db, log_id=log_id, returned=returned)
    if db_log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return db_log

@app.delete("/logs/{log_id}")
def delete_daily_log(log_id: int, db: Session = Depends(get_db)):
    success = crud.delete_daily_log(db, log_id)
    if not success:
        raise HTTPException(status_code=404, detail="Log not found")
    return {"ok": True}

# --- Suppliers ---
@app.post("/suppliers/", response_model=schemas.Supplier)
def create_supplier(supplier: schemas.SupplierCreate, db: Session = Depends(get_db)):
    return crud.create_supplier(db=db, supplier=supplier)

@app.get("/suppliers/", response_model=List[schemas.Supplier])
def read_suppliers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_suppliers(db, skip=skip, limit=limit)

@app.put("/suppliers/{supplier_id}", response_model=schemas.Supplier)
def update_supplier(supplier_id: int, supplier: schemas.SupplierCreate, db: Session = Depends(get_db)):
    updated_supplier = crud.update_supplier(db, supplier_id, supplier)
    if not updated_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return updated_supplier

@app.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    success = crud.delete_supplier(db, supplier_id)
    if not success:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"ok": True}

# --- Purchases ---
@app.post("/purchases/", response_model=schemas.Purchase)
def create_purchase(purchase: schemas.PurchaseCreate, db: Session = Depends(get_db)):
    return crud.create_purchase(db=db, purchase=purchase)

@app.get("/purchases/", response_model=List[schemas.Purchase])
def read_purchases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_purchases(db, skip=skip, limit=limit)

@app.delete("/purchases/{purchase_id}")
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):
    success = crud.delete_purchase(db, purchase_id)
    if not success:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return {"ok": True}

# --- Expenses ---
@app.post("/expenses/", response_model=schemas.Expense)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    return crud.create_expense(db=db, expense=expense)

@app.get("/expenses/", response_model=List[schemas.Expense])
def read_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_expenses(db, skip=skip, limit=limit)

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, db: Session = Depends(get_db)):
    success = crud.delete_expense(db, expense_id)
    if not success:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"ok": True}

# --- Collections ---
@app.post("/collections/", response_model=schemas.Collection)
def create_collection(collection: schemas.CollectionCreate, db: Session = Depends(get_db)):
    return crud.create_collection(db=db, collection=collection)

@app.get("/collections/", response_model=List[schemas.Collection])
def read_collections(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_collections(db, skip=skip, limit=limit)

@app.put("/collections/{collection_id}", response_model=schemas.Collection)
def update_collection(collection_id: int, collection: schemas.CollectionUpdate, db: Session = Depends(get_db)):
    db_collection = crud.update_collection(db=db, collection_id=collection_id, collection=collection)
    if not db_collection:
        raise HTTPException(status_code=404, detail="Collection not found")
    return db_collection

@app.delete("/collections/{collection_id}")
def delete_collection(collection_id: int, db: Session = Depends(get_db)):
    success = crud.delete_collection(db, collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"ok": True}

# --- Analytics ---
@app.get("/analytics/top-products")
def get_top_products(month: int = None, year: int = None, period: str = None, metric: str = 'revenue', limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_top_products(db, target_month=month, target_year=year, period=period, metric=metric, limit=limit)


@app.get("/analytics/top-hawkers")
def get_top_hawkers(month: int, year: int, metric: str = 'revenue', limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_top_hawkers(db, target_month=month, target_year=year, metric=metric, limit=limit)

@app.get("/analytics/dashboard-kpis")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    return crud.get_dashboard_kpis(db)

@app.get("/analytics/sales-trend")
def get_sales_trend(db: Session = Depends(get_db)):
    return crud.get_weekly_sales_trend(db)

@app.get("/analytics/low-stock")
def get_low_stock_alerts(limit: int = 5, db: Session = Depends(get_db)):
    return crud.get_low_stock_alerts(db, limit=limit)

@app.get("/analytics/recent-transactions")
def get_recent_transactions(limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_recent_transactions(db, limit=limit)


# --- Notification System & Product Requests ---
@app.get("/notifications/")
def get_notifications(db: Session = Depends(get_db)):
    return crud.get_notifications(db)

@app.delete("/notifications/{notification_id}")
def delete_notification(notification_id: str, db: Session = Depends(get_db)):
    crud.dismiss_notification(db, notification_id)
    return {"ok": True}

@app.delete("/notifications/")
def clear_all_notifications(db: Session = Depends(get_db)):
    crud.clear_all_notifications(db)
    return {"ok": True}


@app.post("/product-requests/", response_model=schemas.ProductRequest)
def create_product_request(req: schemas.ProductRequestCreate, db: Session = Depends(get_db)):
    return crud.create_product_request(db=db, req=req)

@app.get("/product-requests/", response_model=List[schemas.ProductRequest])
def read_product_requests(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_product_requests(db, skip=skip, limit=limit)

# --- Categories ---
@app.post("/categories/", response_model=schemas.Category)
def create_category(cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    return crud.create_category(db=db, cat=cat)

@app.get("/categories/", response_model=List[schemas.Category])
def read_categories(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_categories(db, skip=skip, limit=limit)

@app.put("/categories/{cat_id}", response_model=schemas.Category)
def update_category(cat_id: int, cat: schemas.CategoryCreate, db: Session = Depends(get_db)):
    updated_cat = crud.update_category(db, cat_id, cat)
    if not updated_cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return updated_cat

@app.delete("/categories/{cat_id}")
def delete_category(cat_id: int, db: Session = Depends(get_db)):
    success = crud.delete_category(db, cat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Category not found")
    return {"ok": True}

# --- Product Units ---
@app.post("/units/", response_model=schemas.ProductUnit)
def create_unit(unit: schemas.ProductUnitCreate, db: Session = Depends(get_db)):
    return crud.create_unit(db=db, unit=unit)

@app.get("/units/", response_model=List[schemas.ProductUnit])
def read_units(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_units(db, skip=skip, limit=limit)

@app.put("/units/{unit_id}", response_model=schemas.ProductUnit)
def update_unit(unit_id: int, unit: schemas.ProductUnitCreate, db: Session = Depends(get_db)):
    updated_unit = crud.update_unit(db, unit_id, unit)
    if not updated_unit:
        raise HTTPException(status_code=404, detail="Product Unit not found")
    return updated_unit

@app.delete("/units/{unit_id}")
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    success = crud.delete_unit(db, unit_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product Unit not found")
    return {"ok": True}


# --- Authentication & Users ---
@app.post("/auth/login", response_model=schemas.LoginResponse)
def login(req: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, req.username, req.password, mode=req.mode)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    
    role_assigned = "admin" if (req.mode == "admin" or user.role.lower() in ["admin", "store manager"]) else "user"
    return {
        "ok": True,
        "user": user,
        "role": role_assigned,
        "message": "Login successful"
    }

@app.post("/users/", response_model=schemas.UserAccount)
def create_user(user: schemas.UserAccountCreate, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@app.get("/users/", response_model=List[schemas.UserAccount])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)

@app.put("/users/{user_id}", response_model=schemas.UserAccount)
def update_user(user_id: int, user: schemas.UserAccountCreate, db: Session = Depends(get_db)):
    updated_user = crud.update_user(db, user_id, user)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    success = crud.delete_user(db, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True}
