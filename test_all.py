"""
tests/test_all.py — Product Catalogue Service test suite
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.store import ProductStore
from experiments.ab_router import assign, EXPERIMENTS
from observability.metrics import Metrics

passed = failed = 0

def ok(msg):
    global passed; passed += 1; print(f"  PASS  {msg}")

def fail(msg, detail=""):
    global failed; failed += 1
    print(f"  FAIL  {msg}" + (f": {detail}" if detail else ""))

def assert_eq(a, b, msg):
    if a == b: ok(msg)
    else: fail(msg, f"expected {b!r}, got {a!r}")

def assert_true(cond, msg):
    if cond: ok(msg)
    else: fail(msg)

def assert_gt(a, b, msg):
    if a > b: ok(msg)
    else: fail(msg, f"expected {a} > {b}")

def assert_lte(a, b, msg):
    if a <= b: ok(msg)
    else: fail(msg, f"expected {a} <= {b}")

# ─── Store tests ──────────────────────────────────────────────────────────────

def test_store():
    print("\n=== Product Store ===")
    store = ProductStore()

    # Correct count
    assert_gt(store.count, 0, "store has products")

    # Categories available
    cats = store.all_categories()
    assert_true(len(cats) > 0, "categories returned")
    assert_true("jackets" in cats, "'jackets' category exists")

    # Get by ID
    p = store.get("item_001")
    assert_true(p is not None, "get item_001 returns product")
    assert_eq(p.id, "item_001", "correct product ID")
    assert_eq(p.category, "jackets", "correct category")

    # Get unknown ID
    assert_true(store.get("nonexistent") is None, "unknown ID returns None")

def test_filter_category():
    print("\n=== Filtering ===")
    store = ProductStore()

    # Category filter
    results, _ = store.filter(category="jackets")
    assert_true(len(results) > 0, "jackets filter returns results")
    assert_true(all(p.category == "jackets" for p in results), "all results are jackets")

    # Price filter
    results, _ = store.filter(max_price=30.0)
    assert_true(all(p.price <= 30.0 for p in results), "max_price filter respected")

    results, _ = store.filter(min_price=50.0)
    assert_true(all(p.price >= 50.0 for p in results), "min_price filter respected")

    # Condition filter
    results, _ = store.filter(condition="excellent")
    assert_true(all(p.condition == "excellent" for p in results), "condition filter respected")

    # Brand filter
    results, _ = store.filter(brand="levi's")
    assert_true(all(p.brand.lower() == "levi's" for p in results), "brand filter respected (case-insensitive)")

    # Combined filters
    results, _ = store.filter(category="jackets", condition="excellent")
    assert_true(all(p.category == "jackets" and p.condition == "excellent" for p in results),
                "combined filters applied correctly")

    # Empty result set
    results, _ = store.filter(category="jackets", max_price=1.0)
    assert_eq(results, [], "impossible filter returns empty list")

def test_sorting():
    print("\n=== Sorting ===")
    store = ProductStore()

    # Sort by price ascending
    results, _ = store.filter(sort_by="price", sort_desc=False)
    prices = [p.price for p in results]
    assert_eq(prices, sorted(prices), "price ascending sort correct")

    # Sort by price descending
    results, _ = store.filter(sort_by="price", sort_desc=True)
    prices = [p.price for p in results]
    assert_eq(prices, sorted(prices, reverse=True), "price descending sort correct")

def test_pagination():
    print("\n=== Cursor Pagination ===")
    store = ProductStore()

    # First page
    page1, cursor1 = store.filter(limit=5)
    assert_eq(len(page1), 5, "first page has 5 items")

    # Second page using cursor
    if cursor1:
        page2, cursor2 = store.filter(limit=5, cursor=cursor1)
        assert_true(len(page2) > 0, "second page has results")

        # No overlap between pages
        ids1 = {p.id for p in page1}
        ids2 = {p.id for p in page2}
        assert_eq(len(ids1 & ids2), 0, "no overlap between pages")

    # Limit respected
    results, _ = store.filter(limit=3)
    assert_lte(len(results), 3, "limit=3 respected")

    # Invalid cursor gracefully handled
    results, _ = store.filter(cursor="invalid_cursor_xyz")
    assert_true(len(results) > 0, "invalid cursor falls back to first page")

# ─── A/B router tests ─────────────────────────────────────────────────────────

def test_ab_router():
    print("\n=== A/B Router ===")

    # Known experiment returns valid result
    result = assign("user_001", "ranking_v2")
    assert_true(result is not None, "known experiment returns result")
    assert_true("variant" in result, "result has variant")
    assert_true("bucket" in result, "result has bucket")
    assert_true(result["variant"] in ["control", "bm25_rerank"], "variant is valid")

    # Deterministic — same user always gets same bucket
    r1 = assign("user_abc", "ranking_v2")
    r2 = assign("user_abc", "ranking_v2")
    assert_eq(r1["variant"], r2["variant"], "assignment is deterministic")

    # Different users may get different buckets (statistical)
    variants = {assign(f"user_{i}", "ranking_v2")["variant"] for i in range(100)}
    assert_true(len(variants) > 1, "different users get different variants (distribution check)")

    # Distribution roughly 50/50
    counts = {"control": 0, "bm25_rerank": 0}
    for i in range(1000):
        v = assign(f"user_{i}", "ranking_v2")["variant"]
        counts[v] = counts.get(v, 0) + 1
    ratio = counts["control"] / 1000
    assert_true(0.4 <= ratio <= 0.6, f"control gets ~50% traffic (got {ratio:.2f})")

    # Unknown experiment returns None
    assert_true(assign("user_001", "nonexistent") is None, "unknown experiment returns None")

    # All registered experiments are valid
    for name in EXPERIMENTS:
        result = assign("test_user", name)
        assert_true(result is not None, f"experiment '{name}' assigns correctly")

# ─── Metrics tests ────────────────────────────────────────────────────────────

def test_metrics():
    print("\n=== Observability / Metrics ===")

    m = Metrics()
    m.record_request("/products", 45.2, 200)
    m.record_request("/products", 32.1, 200)
    m.record_request("/products", 88.7, 400)

    summary = m.summary()
    assert_true("/products" in summary, "/products in metrics summary")
    assert_eq(summary["/products"]["requests"], 3, "request count correct")
    assert_eq(summary["/products"]["errors"], 1, "error count correct")
    assert_gt(summary["/products"]["p95_ms"], 0, "p95 latency computed")

# ─── API integration tests ────────────────────────────────────────────────────

def test_api():
    print("\n=== API Integration ===")
    try:
        from fastapi.testclient import TestClient
        from api.main import app
        client = TestClient(app)

        # Health
        r = client.get("/health")
        assert_eq(r.status_code, 200, "GET /health returns 200")
        assert_eq(r.json()["status"], "ok", "health status is ok")
        assert_gt(r.json()["product_count"], 0, "health reports products")

        # Products list
        r = client.get("/products")
        assert_eq(r.status_code, 200, "GET /products returns 200")
        data = r.json()
        assert_true("results" in data, "/products response has results")
        assert_true("next_cursor" in data, "/products response has next_cursor")
        assert_gt(len(data["results"]), 0, "/products returns products")

        # Filter by category
        r = client.get("/products?category=jackets")
        assert_eq(r.status_code, 200, "GET /products?category=jackets returns 200")
        results = r.json()["results"]
        assert_true(all(p["category"] == "jackets" for p in results), "all results are jackets")

        # Filter by price
        r = client.get("/products?max_price=30")
        results = r.json()["results"]
        assert_true(all(p["price"] <= 30 for p in results), "max_price filter in API")

        # Get single product
        r = client.get("/products/item_001")
        assert_eq(r.status_code, 200, "GET /products/item_001 returns 200")
        assert_eq(r.json()["id"], "item_001", "correct product returned")

        # 404 for unknown product
        r = client.get("/products/nonexistent")
        assert_eq(r.status_code, 404, "GET /products/nonexistent returns 404")

        # Invalid condition
        r = client.get("/products?condition=invalid")
        assert_eq(r.status_code, 400, "invalid condition returns 400")

        # Experiment assignment
        r = client.get("/experiments/ranking_v2", headers={"x-user-id": "user_test"})
        assert_eq(r.status_code, 200, "GET /experiments/ranking_v2 returns 200")
        assert_true("variant" in r.json(), "experiment response has variant")

        # Unknown experiment 404
        r = client.get("/experiments/nonexistent")
        assert_eq(r.status_code, 404, "unknown experiment returns 404")

        # Pagination via API
        r1 = client.get("/products?limit=5")
        cursor = r1.json().get("next_cursor")
        if cursor:
            r2 = client.get(f"/products?limit=5&cursor={cursor}")
            assert_eq(r2.status_code, 200, "paginated request returns 200")
            ids1 = {p["id"] for p in r1.json()["results"]}
            ids2 = {p["id"] for p in r2.json()["results"]}
            assert_eq(len(ids1 & ids2), 0, "no overlap between API pages")

    except ImportError:
        print("  SKIP  API tests (fastapi/httpx not installed)")

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Product Catalogue Service — Test Suite")
    print("=" * 55)

    test_store()
    test_filter_category()
    test_sorting()
    test_pagination()
    test_ab_router()
    test_metrics()
    test_api()

    print(f"\n{'='*55}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*55}\n")
    sys.exit(1 if failed else 0)
