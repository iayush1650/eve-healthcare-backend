# 🏥 EVE Healthcare — Diagnostic Test Booking Service

A production-ready backend service for diagnostic test bookings and simulated payments, built with **FastAPI**, **PostgreSQL**, and **Redis**.

> Built as part of the **EVE Healthcare SDE Intern — Backend Engineering Assignment**.

---

## 🛠️ Skills & Technologies Used

### Backend & Framework
- **Python 3.12** — Primary programming language
- **FastAPI** — High-performance async web framework with auto-generated OpenAPI docs
- **Uvicorn** — ASGI server for running the application

### Database & ORM
- **PostgreSQL 16** — Primary relational database (production)
- **SQLite** — Lightweight DB for local development and testing
- **SQLAlchemy 2.0** — ORM with declarative models, relationships, and connection pooling
- **Alembic-ready schema** — Table creation via `Base.metadata.create_all()`

### Authentication & Security
- **JWT (JSON Web Tokens)** — Stateless token-based authentication using `python-jose`
- **bcrypt** — Industry-standard password hashing
- **Bearer token scheme** — Swagger UI compatible auth flow

### API Design & Validation
- **RESTful API design** — Proper HTTP methods, status codes, and resource naming
- **Pydantic v2** — Request/response validation with custom validators
- **Pagination** — Cursor-based pagination on all list endpoints
- **Rate Limiting** — `slowapi` for request throttling per IP

### DevOps & Containerization
- **Docker** — Multi-stage Dockerfile for containerized deployment
- **Docker Compose** — Full stack orchestration (PostgreSQL + Redis + API)
- **Environment-based config** — `.env` file support via `pydantic-settings`

### Testing
- **pytest** — 55+ test cases covering all endpoints, caching, and edge cases
- **httpx + TestClient** — FastAPI test client for integration testing
- **In-memory SQLite** — Isolated test database per test case
- **pytest-cov** — Code coverage reporting

### Observability & Logging
- **structlog** — Structured JSON logging with context variables
- **Request validation error handler** — Custom structured error responses

### Caching
- **Redis 7** — TTL-based caching for centre listings (5 min), centre details (15 min), and test listings (5 min)
- **Graceful degradation** — App works without Redis; cache operations return `None`/`False` silently
- **Pattern-based invalidation** — Cache busted on create/update operations using `SCAN` (non-blocking)
- **Health endpoint** — `/health/cache` reports Redis connectivity and memory usage

### Background Jobs & Webhook Retry
- **Celery 5.4** — Distributed task queue with Redis as broker and result backend
- **Async webhook processing** — `POST /payments/webhook/?async_processing=true` queues webhooks for background processing
- **Exponential backoff retry** — Failed webhooks retry with ~10s → 20s → 40s → 80s → 160s delays (5 retries max)
- **Retry jitter** — Randomized delays to prevent thundering herd on retries
- **Dead-letter queue** — Tasks that exhaust all retries are rejected for manual inspection
- **Failed webhook scanner** — Celery Beat periodic task to re-queue unprocessed `WebhookEvent` records
- **Docker services** — `celery_worker` and `celery_beat` containers in `docker-compose.yml`

### Code Architecture
- **Layered architecture** — Models → Schemas → Services → API routes
- **Dependency injection** — FastAPI `Depends()` for DB sessions and auth
- **Custom exception hierarchy** — `NotFoundException`, `ConflictException`, etc.
- **Service layer pattern** — Business logic separated from route handlers

---

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/iayush1650/eve-healthcare-backend.git
cd eve-healthcare-backend

# Start all services (PostgreSQL + Redis + API)
docker-compose up --build

# Seed the database (in another terminal)
docker-compose exec api python seed_data.py
```

The API will be available at **http://localhost:8000**.

### Option 2: Local Development

```bash
# Prerequisites: Python 3.12+, PostgreSQL, Redis

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your database credentials

# Run the server
uvicorn app.main:app --reload --port 8000

# Seed sample data
python seed_data.py
```

---

## 📖 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## 📡 API Endpoints

### Health Check
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | ❌ | Service health check |

### Authentication
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/signup` | ❌ | Register a new user |
| POST | `/api/v1/auth/login` | ❌ | Login and get JWT token |

### Diagnostic Centres & Tests
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/centres/` | ❌ | Create a diagnostic centre |
| GET | `/api/v1/centres/` | ❌ | List centres (pagination + location filter) |
| GET | `/api/v1/centres/{id}` | ❌ | Get centre details with available tests |
| POST | `/api/v1/centres/tests` | ❌ | Create a diagnostic test |
| GET | `/api/v1/centres/tests/all` | ❌ | List all tests (pagination + category filter) |
| POST | `/api/v1/centres/tests/link` | ❌ | Link test to centre with pricing |

### Bookings (Authenticated)
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/bookings/` | ✅ | Create a booking |
| GET | `/api/v1/bookings/` | ✅ | List user's bookings (paginated) |
| GET | `/api/v1/bookings/{id}` | ✅ | Get booking details |
| POST | `/api/v1/bookings/{id}/cancel` | ✅ | Cancel a booking |

### Payments
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/payments/` | ✅ | Process simulated payment |
| POST | `/api/v1/payments/webhook/` | ❌ | Payment webhook (idempotent) |

---

## 💡 Example Requests

### 1. Sign Up
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@example.com",
    "full_name": "Ayush Kumar",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "a1b2c3d4-...",
    "email": "patient@example.com",
    "full_name": "Ayush Kumar",
    "is_active": true
  }
}
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@example.com",
    "password": "securepassword123"
  }'
```

### 3. List Centres (with Location Filter)
```bash
curl http://localhost:8000/api/v1/centres/?location=Mumbai
```

### 4. Create a Booking
```bash
curl -X POST http://localhost:8000/api/v1/bookings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "centre_test_id": "<centre-test-uuid>",
    "appointment_datetime": "2026-10-15T10:00:00+05:30"
  }'
```

### 5. Process Payment
```bash
curl -X POST http://localhost:8000/api/v1/payments/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{
    "booking_id": "<booking-uuid>"
  }'
```

### 6. Webhook (Simulated Payment Provider)
```bash
curl -X POST http://localhost:8000/api/v1/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "EVT-12345",
    "event_type": "payment.completed",
    "transaction_id": "TXN-ABCDEF123456",
    "status": "SUCCESS",
    "amount": "500.00"
  }'
```

---

## 🗄️ Database Schema

```
┌──────────────────┐       ┌──────────────────────┐       ┌──────────────────┐
│     users        │       │  diagnostic_centres   │       │ diagnostic_tests │
├──────────────────┤       ├──────────────────────┤       ├──────────────────┤
│ id (UUID, PK)    │       │ id (UUID, PK)         │       │ id (UUID, PK)    │
│ email (unique)   │       │ name                  │       │ name             │
│ full_name        │       │ location              │       │ description      │
│ phone            │       │ address               │       │ category         │
│ password_hash    │       │ phone                 │       │ created_at       │
│ is_active        │       │ is_active             │       │ updated_at       │
│ created_at       │       │ created_at            │       └────────┬─────────┘
│ updated_at       │       │ updated_at            │                │
└────────┬─────────┘       └──────────┬────────────┘                │
         │                            │                             │
         │                            └──────────┐    ┌─────────────┘
         │                                       │    │
         │                            ┌──────────┴────┴──────────┐
         │                            │      centre_tests        │
         │                            ├──────────────────────────┤
         │                            │ id (UUID, PK)            │
         │                            │ centre_id (FK)           │
         │                            │ test_id (FK)             │
         │                            │ price (Decimal)          │
         │                            │ is_available             │
         │                            │ UNIQUE(centre_id,test_id)│
         │                            └──────────┬───────────────┘
         │                                       │
         │              ┌────────────────────────┤
         │              │                        │
         │   ┌──────────┴────────────┐           │
         │   │      bookings         │           │
         │   ├───────────────────────┤           │
         └──►│ id (UUID, PK)         │◄──────────┘
             │ user_id (FK)          │
             │ centre_test_id (FK)   │
             │ appointment_datetime  │
             │ amount (Decimal)      │
             │ status (ENUM)         │
             │ created_at            │
             │ updated_at            │
             └──────────┬────────────┘
                        │
                        │  1:1
             ┌──────────┴────────────┐
             │      payments         │
             ├───────────────────────┤
             │ id (UUID, PK)         │
             │ booking_id (FK,unique)│
             │ transaction_id (uniq) │
             │ amount (Decimal)      │
             │ status (ENUM)         │
             │ payment_method        │
             │ created_at            │
             │ updated_at            │
             └───────────────────────┘

             ┌───────────────────────┐
             │    webhook_events     │
             ├───────────────────────┤
             │ id (UUID, PK)         │
             │ event_id (unique)     │
             │ event_type            │
             │ payload (JSONB)       │
             │ processed             │
             │ created_at            │
             └───────────────────────┘
```

### Key Design Decisions

- **Centre-Test junction table (`centre_tests`)**: Different centres can offer the same test at different prices. The `UNIQUE(centre_id, test_id)` constraint prevents duplicate listings.
- **One payment per booking**: The `unique` constraint on `payments.booking_id` enforces this at the database level.
- **Webhook idempotency**: The `webhook_events` table records every `event_id`. Duplicate events are detected and ignored before any state mutation occurs.
- **UUID primary keys**: Prevent ID enumeration attacks and are safe for distributed systems.

### Booking State Machine

```
PENDING ──► CONFIRMED  (on payment success)
   │              │
   │              ▼
   │          CANCELLED  (user-initiated)
   │
   └──────► FAILED      (on payment failure)
```

---

## 🛡️ Edge Cases Handled

| # | Edge Case | How It's Handled |
|---|-----------|-----------------|
| 1 | Duplicate webhook events | `event_id` deduplication via `webhook_events` table |
| 2 | Double payment for same booking | `UNIQUE` constraint on `payments.booking_id` + status check |
| 3 | Booking with past date | Pydantic validator rejects past `appointment_datetime` |
| 4 | Unauthorized booking access | User ID comparison → returns `403 Forbidden` |
| 5 | Payment for another user's booking | User ID validation in `PaymentService` → returns `400` |
| 6 | Invalid booking ID in payment | Returns `404 Not Found` with descriptive message |
| 7 | Cancel non-cancellable booking | Status check → only PENDING/CONFIRMED can be cancelled |
| 8 | Inactive diagnostic centre | Booking creation checks `centre.is_active` |
| 9 | Unavailable test at centre | Booking creation checks `centre_test.is_available` |
| 10 | Duplicate user registration | Unique email constraint → returns `409 Conflict` |
| 11 | Invalid/expired JWT token | Returns `401 Unauthorized` with `WWW-Authenticate` header |
| 12 | Malformed request body | Pydantic validation with structured error response |
| 13 | Duplicate centre-test linking | Unique constraint check → returns `409 Conflict` |

---

## 🧪 Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=html -v

# Run specific test modules
pytest tests/test_auth.py -v
pytest tests/test_bookings.py -v
pytest tests/test_payments.py -v
pytest tests/test_centres.py -v
```

**Test Summary**: 55+ test cases covering authentication, bookings, centres, payments, webhook idempotency, Redis caching, and Celery integration. Tests use an **in-memory SQLite** database for speed and complete isolation.

---

## 📁 Project Structure

```
eve-healthcare-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI app entry point with lifespan
│   ├── config.py              # Pydantic settings (env-based config)
│   ├── database.py            # SQLAlchemy engine & session management
│   ├── celery_app.py          # Celery configuration (Redis broker)
│   ├── core/
│   │   ├── security.py        # JWT creation/verification & bcrypt hashing
│   │   ├── exceptions.py      # Custom HTTP exception hierarchy
│   │   └── cache.py           # Redis caching utility (TTL, invalidation)
│   ├── models/
│   │   ├── user.py            # User model
│   │   ├── centre.py          # DiagnosticCentre model
│   │   ├── test.py            # DiagnosticTest & CentreTest (junction) models
│   │   ├── booking.py         # Booking model with BookingStatus enum
│   │   └── payment.py         # Payment & WebhookEvent models
│   ├── schemas/
│   │   ├── user.py            # Auth request/response schemas
│   │   ├── centre.py          # Centre schemas with nested tests
│   │   ├── test.py            # Test & CentreTest schemas
│   │   ├── booking.py         # Booking schemas with datetime validator
│   │   └── payment.py         # Payment & webhook schemas
│   ├── services/
│   │   ├── auth.py            # Signup/login business logic
│   │   ├── booking.py         # Booking CRUD & validation logic
│   │   └── payment.py         # Payment processing & idempotent webhooks
│   ├── tasks/
│   │   ├── __init__.py
│   │   └── webhook_tasks.py   # Celery tasks: async webhook + retry scanner
│   └── api/
│       ├── deps.py            # Shared dependencies (auth, DB session)
│       ├── auth.py            # Auth routes (signup, login)
│       ├── centres.py         # Centre & test routes (with Redis caching)
│       ├── bookings.py        # Booking routes (CRUD + cancel)
│       └── payments.py        # Payment & webhook routes (sync + async)
├── tests/
│   ├── conftest.py            # Test fixtures & in-memory DB setup
│   ├── test_auth.py           # 9 auth tests
│   ├── test_centres.py        # 11 centre & test tests
│   ├── test_bookings.py       # 11 booking tests
│   ├── test_payments.py       # 12 payment & webhook tests
│   ├── test_cache.py          # 8 Redis caching tests
│   └── test_celery.py         # 6 Celery & async webhook tests
├── seed_data.py               # Database seeder (3 centres, 8 tests)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## 📌 Important Assumptions

1. **No real payment gateway** — Payments are simulated with a 70% success / 30% failure rate using Python's `random.choices()`.
2. **No admin role** — Centre/test management endpoints are open for simplicity. In production, these would be restricted to admin users with RBAC.
3. **Single payment per booking** — Each booking can have at most one payment record, enforced by a database unique constraint.
4. **Webhook authentication** — In production, webhooks would verify an HMAC signature from the payment provider. Currently, the endpoint is open for demonstration.
5. **UTC timezone** — All timestamps are stored and compared in UTC for consistency.
6. **No email verification** — User accounts are active immediately upon signup.

---

## 🔮 What I Would Improve with More Time

- **Alembic migrations** — Add proper database migration versioning instead of `create_all()`.
- **Admin role & RBAC** — Role-based access control for centre/test management.
- **Webhook signature verification** — HMAC-based signature validation for webhook security.
- **Appointment slot management** — Prevent double-booking of time slots at centres.
- **Email notifications** — Send booking confirmation and payment status emails via Celery.
- **API versioning strategy** — Header-based or URL-based versioning for future API evolution.
- **Load testing** — k6 or Locust scripts for performance benchmarking.
- **CI/CD pipeline** — GitHub Actions for automated testing, linting, and deployment.

---

## 📜 License

Built for the EVE Healthcare SDE Intern Assignment.
