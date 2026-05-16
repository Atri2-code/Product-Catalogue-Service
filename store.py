"""
db/store.py

In-memory product store — simulates a PostgreSQL-backed catalogue.
In production this would use SQLAlchemy async + connection pooling.
"""

from __future__ import annotations
import base64
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple


@dataclass
class Product:
    id: str
    title: str
    category: str
    price: float
    condition: str          # excellent | good | fair | poor
    brand: str
    size: str
    description: str
    seller_id: str
    created_at: str         # ISO timestamp string


class ProductStore:
    """
    Thread-safe in-memory product store.
    Production equivalent: async SQLAlchemy + PostgreSQL.
    """

    def __init__(self):
        self._products: Dict[str, Product] = {}
        self._seed()

    def _seed(self):
        import datetime
        base_date = datetime.datetime(2024, 1, 1)
        products = [
            ("item_001", "Vintage Levi's 501 Denim Jacket",   "jackets",  45.0,  "good",      "Levi's",    "M",   "Classic 501 trucker jacket in medium wash. Minor fading.", "seller_a", 0),
            ("item_002", "90s Oversized Denim Jacket Blue",   "jackets",  32.0,  "fair",      "Unknown",   "L",   "Oversized fit, some wear on cuffs.",                      "seller_b", 1),
            ("item_003", "Levi's Strauss Jean Jacket Classic","jackets",  55.0,  "excellent", "Levi's",    "S",   "Barely worn, original buttons, no fading.",               "seller_c", 2),
            ("item_004", "Nike Air Max 90 White Trainers",    "shoes",    75.0,  "good",      "Nike",      "10",  "Size UK10, cleaned, slight sole yellowing.",              "seller_a", 3),
            ("item_005", "Adidas Samba OG Black White",       "shoes",    90.0,  "excellent", "Adidas",    "9",   "UK9, worn twice, box included.",                         "seller_d", 4),
            ("item_006", "Rolling Stones 1994 Tour Tee",      "tops",     28.0,  "good",      "Band Tee",  "L",   "Authentic 1994 Voodoo Lounge tour tee.",                 "seller_b", 5),
            ("item_007", "Y2K Baby Tee Pink Rhinestone",      "tops",     15.0,  "good",      "Unknown",   "XS",  "Y2K style pink baby tee with rhinestone detail.",        "seller_e", 6),
            ("item_008", "Carhartt WIP Detroit Jacket Brown", "jackets",  85.0,  "excellent", "Carhartt",  "M",   "Hamilton brown, worn three times.",                      "seller_c", 7),
            ("item_009", "Ralph Lauren Polo Shirt Navy",      "tops",     22.0,  "good",      "Ralph Lauren","M", "Classic polo, navy, size M, small logo.",                "seller_a", 8),
            ("item_010", "Vintage Wrangler Denim Shirt",      "tops",     30.0,  "fair",      "Wrangler",  "L",   "Western style, snap buttons, light fade.",               "seller_f", 9),
            ("item_011", "New Balance 574 Grey Trainers",     "shoes",    60.0,  "good",      "New Balance","8",  "UK8, suede panels, light use.",                          "seller_b",10),
            ("item_012", "Dr Martens 1460 Black Boots",       "shoes",    95.0,  "excellent", "Dr Martens","7",   "UK7, polished, no scuffs.",                              "seller_g",11),
            ("item_013", "Levi's 501 Straight Jeans W30 L32","bottoms",  40.0,  "good",      "Levi's",    "W30","Vintage wash, W30 L32, slight knee fade.",               "seller_a",12),
            ("item_014", "Corduroy Wide Leg Trousers Brown",  "bottoms",  25.0,  "good",      "Unknown",   "M",   "Brown cord, wide leg, vintage fit.",                     "seller_h",13),
            ("item_015", "Champion Reverse Weave Hoodie Grey","tops",     35.0,  "good",      "Champion",  "L",   "Classic reverse weave, grey, minimal pilling.",          "seller_c",14),
        ]
        for pid, title, cat, price, cond, brand, size, desc, seller, offset in products:
            dt = (base_date + datetime.timedelta(days=offset)).isoformat()
            self._products[pid] = Product(
                id=pid, title=title, category=cat, price=price, condition=cond,
                brand=brand, size=size, description=desc, seller_id=seller, created_at=dt
            )

    def filter(
        self,
        category: Optional[str] = None,
        max_price: Optional[float] = None,
        min_price: Optional[float] = None,
        condition: Optional[str] = None,
        brand: Optional[str] = None,
        sort_by: str = "created_at",
        sort_desc: bool = True,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Product], Optional[str]]:
        """
        Filter and paginate products using cursor-based pagination.

        Returns:
            (results, next_cursor) — next_cursor is None if no more pages.
        """
        products = list(self._products.values())

        # Apply filters
        if category:
            products = [p for p in products if p.category == category]
        if max_price is not None:
            products = [p for p in products if p.price <= max_price]
        if min_price is not None:
            products = [p for p in products if p.price >= min_price]
        if condition:
            products = [p for p in products if p.condition == condition]
        if brand:
            products = [p for p in products if p.brand.lower() == brand.lower()]

        # Sort
        key_fn = {
            "price":      lambda p: p.price,
            "created_at": lambda p: p.created_at,
            "title":      lambda p: p.title,
        }.get(sort_by, lambda p: p.created_at)

        products = sorted(products, key=key_fn, reverse=sort_desc)

        # Cursor decode — cursor encodes the last seen id
        start_idx = 0
        if cursor:
            try:
                cursor_data = json.loads(base64.b64decode(cursor).decode())
                last_id = cursor_data.get("last_id")
                ids = [p.id for p in products]
                if last_id in ids:
                    start_idx = ids.index(last_id) + 1
            except Exception:
                pass

        page = products[start_idx:start_idx + limit]

        # Next cursor
        next_cursor = None
        if len(page) == limit and start_idx + limit < len(products):
            next_cursor = base64.b64encode(
                json.dumps({"last_id": page[-1].id}).encode()
            ).decode()

        return page, next_cursor

    def get(self, product_id: str) -> Optional[Product]:
        return self._products.get(product_id)

    def all_categories(self) -> List[str]:
        return sorted(set(p.category for p in self._products.values()))

    @property
    def count(self) -> int:
        return len(self._products)


# Singleton
_store: Optional[ProductStore] = None

def get_store() -> ProductStore:
    global _store
    if _store is None:
        _store = ProductStore()
    return _store
