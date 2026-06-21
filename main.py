from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import models, schemas, crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Daily Consignment Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow frontend to access API
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/products/", response_model=schemas.Product)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db=db, product=product)

@app.get("/products/", response_model=List[schemas.Product])
def read_products(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_products(db, skip=skip, limit=limit)

@app.post("/sellers/", response_model=schemas.Seller)
def create_seller(seller: schemas.SellerCreate, db: Session = Depends(get_db)):
    return crud.create_seller(db=db, seller=seller)

@app.get("/sellers/", response_model=List[schemas.Seller])
def read_sellers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_sellers(db, skip=skip, limit=limit)

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

@app.get("/analytics/top-products")
def get_top_products(month: int, year: int, metric: str = 'revenue', limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_top_products(db, target_month=month, target_year=year, metric=metric, limit=limit)

@app.get("/analytics/top-sellers")
def get_top_sellers(month: int, year: int, metric: str = 'revenue', limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_top_sellers(db, target_month=month, target_year=year, metric=metric, limit=limit)
