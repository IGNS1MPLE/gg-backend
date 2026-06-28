from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models, schemas, crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

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

# --- Purchases ---
@app.post("/purchases/", response_model=schemas.Purchase)
def create_purchase(purchase: schemas.PurchaseCreate, db: Session = Depends(get_db)):
    return crud.create_purchase(db=db, purchase=purchase)

@app.get("/purchases/", response_model=List[schemas.Purchase])
def read_purchases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_purchases(db, skip=skip, limit=limit)

# --- Expenses ---
@app.post("/expenses/", response_model=schemas.Expense)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    return crud.create_expense(db=db, expense=expense)

@app.get("/expenses/", response_model=List[schemas.Expense])
def read_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_expenses(db, skip=skip, limit=limit)

# --- Collections ---
@app.post("/collections/", response_model=schemas.Collection)
def create_collection(collection: schemas.CollectionCreate, db: Session = Depends(get_db)):
    return crud.create_collection(db=db, collection=collection)

@app.get("/collections/", response_model=List[schemas.Collection])
def read_collections(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_collections(db, skip=skip, limit=limit)

# --- Analytics ---
@app.get("/analytics/top-products")
def get_top_products(month: int, year: int, metric: str = 'revenue', limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_top_products(db, target_month=month, target_year=year, metric=metric, limit=limit)

@app.get("/analytics/top-hawkers")
def get_top_hawkers(month: int, year: int, metric: str = 'revenue', limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_top_hawkers(db, target_month=month, target_year=year, metric=metric, limit=limit)

@app.get("/analytics/dashboard-kpis")
def get_dashboard_kpis(db: Session = Depends(get_db)):
    return crud.get_dashboard_kpis(db)

@app.get("/analytics/sales-trend")
def get_sales_trend(db: Session = Depends(get_db)):
    return crud.get_weekly_sales_trend(db)
