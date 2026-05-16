"""
api/main.py — Product Catalogue Service
"""

from __future__ import annotations
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Header
from pydantic import BaseModel

from db.store import get_store, Product
from experiments.ab_router import assign, list_experiments
from observability.metrics import get_metrics

app = FastAPI(
    title="Product Catalogue Service",
    description="High-throughput product discovery API with filtering, cursor pagination, A/B testing, and observability.",
    version="1.0.0",
)

# ─── Models ───────────────────────────────────────────────────────────────────

class ProductResponse(BaseModel):
    id: str
    title: str
    category: str
    price: float
    condition: str
    brand: str
    size: str
    description: str

class ProductListResponse(BaseModel):
    results: List[ProductResponse]
    total: int
    next_cursor: Optional[str]
    latency_ms: float

class HealthResponse(BaseModel):
    status: str
    product_count: int
    categories: List[str]

class MetricsResponse(BaseModel):
    endpoints: dict

class ExperimentResponse(BaseModel):
    experiment: str
    bucket: str
    variant: str

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health():
    store = get_store()
    return HealthResponse(
        status="ok",
        product_count=store.count,
        categories=store.all_categories(),
    )

@app.get("/metrics", response_model=MetricsResponse)
def metrics():
    return MetricsResponse(endpoints=get_metrics().summary())

@app.get("/products", response_model=ProductListResponse)
def list_products(
    category:  Optional[str]   = Query(None, description="Filter by category"),
    max_price: Optional[float]  = Query(None, ge=0, description="Maximum price"),
    min_price: Optional[float]  = Query(None, ge=0, description="Minimum price"),
    condition: Optional[str]   = Query(None, description="Product condition: excellent|good|fair|poor"),
    brand:     Optional[str]   = Query(None, description="Filter by brand"),
    sort_by:   str              = Query("created_at", description="Sort field: price|created_at|title"),
    sort_desc: bool             = Query(True, description="Sort descending"),
    limit:     int              = Query(10, ge=1, le=100),
    cursor:    Optional[str]   = Query(None, description="Pagination cursor"),
    x_user_id: Optional[str]   = Header(None, description="User ID for A/B assignment"),
):
    t0 = time.perf_counter()
    store = get_store()

    if sort_by not in ("price", "created_at", "title"):
        raise HTTPException(status_code=400, detail="sort_by must be: price, created_at, title")

    if condition and condition not in ("excellent", "good", "fair", "poor"):
        raise HTTPException(status_code=400, detail="condition must be: excellent, good, fair, poor")

    products, next_cursor = store.filter(
        category=category,
        max_price=max_price,
        min_price=min_price,
        condition=condition,
        brand=brand,
        sort_by=sort_by,
        sort_desc=sort_desc,
        limit=limit,
        cursor=cursor,
    )

    latency_ms = round((time.perf_counter() - t0) * 1000, 2)
    get_metrics().record_request("/products", latency_ms, 200)

    return ProductListResponse(
        results=[
            ProductResponse(
                id=p.id, title=p.title, category=p.category,
                price=p.price, condition=p.condition,
                brand=p.brand, size=p.size, description=p.description,
            )
            for p in products
        ],
        total=len(products),
        next_cursor=next_cursor,
        latency_ms=latency_ms,
    )

@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: str):
    store = get_store()
    product = store.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")
    return ProductResponse(
        id=product.id, title=product.title, category=product.category,
        price=product.price, condition=product.condition,
        brand=product.brand, size=product.size, description=product.description,
    )

@app.get("/experiments/{experiment}", response_model=ExperimentResponse)
def get_experiment(
    experiment: str,
    x_user_id: Optional[str] = Header(None),
):
    user_id = x_user_id or "anonymous"
    result = assign(user_id, experiment)
    if not result:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment}' not found")
    return ExperimentResponse(**result)

@app.get("/experiments")
def list_experiments_route():
    return {"experiments": list_experiments()}

@app.get("/")
def root():
    return {"message": "Product Catalogue Service — see /docs for API reference"}
