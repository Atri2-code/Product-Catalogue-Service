# 🛍️ Product Catalogue Microservice

> A high-throughput backend service for product discovery — paginated filtering, observability, A/B testing hooks, and full lifecycle ownership. Built in Python, deployed on AWS.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![AWS](https://img.shields.io/badge/AWS-EC2%20%7C%20S3%20%7C%20CloudWatch-orange) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue) ![Tests](https://img.shields.io/badge/tests-passing-brightgreen) ![License](https://img.shields.io/badge/license-MIT-green)

---

## 🧭 About

Built to practice owning a backend service end-to-end — from schema design through to deployment and observability. Simulates the kind of product catalogue backend that powers a consumer marketplace (filtering, ranking, pagination, A/B testing) at scale.

Designed with 1M+ daily active user load patterns in mind: connection pooling, query optimisation, structured logging, and metric instrumentation from day one.

---

## ✨ Features

- 🔍 **Multi-filter Search** — filter by category, price range, condition, size, and brand with compound index support
- 📄 **Cursor-based Pagination** — stable, efficient pagination for large result sets (no OFFSET drift)
- 🧪 **A/B Testing Hooks** — per-request experiment assignment with feature flag support for ranking experiments
- 📊 **Observability** — structured JSON logging, Prometheus metrics endpoint, CloudWatch integration
- 🔒 **Input Validation** — Pydantic models with strict type enforcement on all endpoints
- ♻️ **Full Lifecycle Ownership** — schema migrations (Alembic), CI/CD via GitHub Actions, blue/green deployment on AWS EC2

---

## 🏗️ Architecture

```
product-catalogue-service/
├── api/
│   ├── main.py               # FastAPI app
│   ├── routes/
│   │   ├── products.py       # GET /products — filter, paginate, sort
│   │   ├── search.py         # GET /search — full-text + filter
│   │   └── health.py         # GET /health, /metrics
│   └── models.py             # Pydantic request/response models
├── db/
│   ├── database.py           # SQLAlchemy async engine + connection pool
│   ├── models.py             # ORM models
│   └── migrations/           # Alembic migration files
├── experiments/
│   ├── ab_router.py          # A/B experiment assignment logic
│   └── feature_flags.py      # Runtime feature flag evaluation
├── observability/
│   ├── logging.py            # Structured JSON logger
│   └── metrics.py            # Prometheus counter/histogram setup
├── tests/
│   ├── test_products.py      # Filter, pagination, sort correctness
│   ├── test_search.py        # Full-text search accuracy
│   ├── test_ab.py            # Experiment assignment distribution
│   └── conftest.py           # Pytest fixtures, test DB setup
├── infra/
│   ├── deploy.sh             # EC2 blue/green deployment
│   └── cloudwatch.json       # CloudWatch log group config
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions: lint, test, deploy
└── README.md
```

---

## 🚀 Getting Started

```bash
git clone https://github.com/Atri2-code/product-catalogue-service
cd product-catalogue-service
pip install -r requirements.txt

# Start PostgreSQL
docker-compose up -d db

# Run migrations
alembic upgrade head

# Seed sample data
python scripts/seed.py --count 10000

# Start API
uvicorn api.main:app --reload
```

---

## 📊 Example Endpoints

```bash
# Filter products
GET /products?category=jackets&condition=good&max_price=50&limit=20&cursor=eyJpZCI6MTAwfQ==

# Full-text search with filters
GET /search?q=vintage+levi&category=denim&sort=relevance&limit=10

# Health check
GET /health
# → { "status": "ok", "db": "connected", "uptime_s": 3821 }

# Metrics
GET /metrics
# → Prometheus format: request latency histograms, error rates, cache hit ratio
```

---

## 🧪 Tests

```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

Covers:
- Filter correctness (single and compound filters)
- Cursor pagination stability across inserts
- A/B assignment distribution (chi-squared test for uniformity)
- API contract validation
- DB connection pool behaviour under load

---

## 🔬 A/B Testing

Each request is assigned to an experiment bucket based on a hash of the user ID:

```python
experiment = ab_router.assign(user_id="u_4821", experiment="ranking_v2")
# → { "bucket": "treatment", "variant": "bm25_rerank" }
```

Experiment results are logged to CloudWatch for downstream analysis.

---

## ☁️ AWS Deployment

```bash
# Blue/green deploy to EC2
bash infra/deploy.sh --env prod --region eu-west-2 --strategy blue-green

# View logs
aws logs tail /prod/product-catalogue --follow
```

---

## 💡 What I Learned

- Why cursor-based pagination outperforms OFFSET for large, frequently-updated datasets
- How A/B testing infrastructure integrates into a request lifecycle without adding latency
- Prometheus metric instrumentation patterns for backend services
- Blue/green deployment to eliminate downtime during releases
- SQLAlchemy async engine configuration for high-concurrency workloads

---

## 📌 Topics

`python` `fastapi` `postgresql` `aws` `ec2` `backend` `microservice` `ab-testing` `observability` `prometheus` `pagination` `github-actions` `sqlalchemy`

---

## 📄 License

MIT
