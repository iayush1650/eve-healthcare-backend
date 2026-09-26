# EVE Healthcare — Diagnostic Test Booking Service

A backend service for diagnostic test bookings and simulated payments, built with **FastAPI**, **PostgreSQL**, and **Redis**.

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI (Python 3.12) |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.0 |
| Auth | JWT (python-jose) + bcrypt |
| Caching | Redis 7 |
| Containerization | Docker + Docker Compose |
| Testing | pytest + httpx |
| Docs | Swagger UI (auto-generated) |
| Logging | structlog (structured JSON) |
| Rate Limiting | slowapi |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and run
git clone <repo-url>
cd eve-healthcare

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

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## API Endpoints

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
| GET | `/api/v1/centres/` | ❌ | List centres (with pagination & location filter) |
| GET | `/api/v1/centres/{id}` | ❌ | Get centre details with tests |
| POST | `/api/v1/centres/tests` | ❌ | Create a diagnostic test |
| GET | `/api/v1/centres/tests/all` | ❌ | List all tests (with pagination & category filter) |
| POST | `/api/v1/centres/tests/link` | ❌ | Link test to centre with pricing |

### Bookings
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/bookings/` | ✅ | Create a booking |
| GET | `/api/v1/bookings/` | ✅ | List user's bookings |
| GET | `/api/v1/bookings/{id}` | ✅ | Get booking details |
| POST | `/api/v1/bookings/{id}/cancel` | ✅ | Cancel a booking |

### Payments
| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/payments/` | ✅ | Process simulated payment |
| POST | `/api/v1/payments/webhook/` | ❌ | Payment webhook (idempotent) |

---

## Example Requests

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

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patient@example.com",
    "password": "securepassword123"
  }'
```

### 3. List Centres
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

## Database Schema

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
- **One payment per booking**: The `unique` constraint on `payments.booking_id` enforces this.
- **Webhook idempotency**: The `webhook_events` table records every `event_id`. Duplicate events are detected and ignored before any state mutation.
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

## Edge Cases Handled

| Edge Case | How It's Handled |
|-----------|-----------------|
| Duplicate webhook events | `event_id` deduplication via `webhook_events` table |
| Double payment for same booking | `UNIQUE` constraint on `payments.booking_id` + status check |
| Booking with past date | Pydantic validator rejects past `appointment_datetime` |
| Unauthorized booking access | User ID comparison with `ForbiddenException` |
| Payment for another user's booking | User ID validation in `PaymentService` |
| Invalid booking ID in payment | Returns 404 with descriptive message |
| Cancel non-pending booking | Status check returns 400 |
| Inactive diagnostic centre | Booking creation checks `centre.is_active` |
| Unavailable test | Booking creation checks `centre_test.is_available` |
| Duplicate user registration | Unique email constraint + 409 Conflict response |
| Invalid/expired JWT | Returns 401 with WWW-Authenticate header |
| Malformed request body | FastAPI/Pydantic validation with structured error response |

---

## Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest --cov=app --cov-report=html -v

# Run specific test file
pytest tests/test_auth.py -v
pytest tests/test_bookings.py -v
pytest tests/test_payments.py -v
```

Tests use an **in-memory SQLite** database for speed and isolation. Each test gets a fresh database.

---

## Project Structure

```
eve-healthcare/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── config.py             # Pydantic settings
│   ├── database.py           # SQLAlchemy engine & session
│   ├── core/
│   │   ├── security.py       # JWT & password utilities
│   │   └── exceptions.py     # Custom HTTP exceptions
│   ├── models/
│   │   ├── user.py           # User model
│   │   ├── centre.py         # DiagnosticCentre model
│   │   ├── test.py           # DiagnosticTest & CentreTest models
│   │   ├── booking.py        # Booking model with status enum
│   │   └── payment.py        # Payment & WebhookEvent models
│   ├── schemas/
│   │   ├── user.py           # Auth request/response schemas
│   │   ├── centre.py         # Centre schemas
│   │   ├── test.py           # Test schemas
│   │   ├── booking.py        # Booking schemas
│   │   └── payment.py        # Payment & webhook schemas
│   ├── services/
│   │   ├── auth.py           # Authentication business logic
│   │   ├── booking.py        # Booking business logic
│   │   └── payment.py        # Payment & webhook business logic
│   └── api/
│       ├── deps.py           # Shared dependencies (auth, DB)
│       ├── auth.py           # Auth routes
│       ├── centres.py        # Centre & test routes
│       ├── bookings.py       # Booking routes
│       └── payments.py       # Payment & webhook routes
├── tests/
│   ├── conftest.py           # Test fixtures
│   ├── test_auth.py          # Auth tests
│   ├── test_centres.py       # Centre & test tests
│   ├── test_bookings.py      # Booking tests
│   └── test_payments.py      # Payment & webhook tests
├── seed_data.py              # Database seeder
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Important Assumptions

1. **No real payment gateway**: Payments are simulated with a 70% success / 30% failure rate.
2. **No admin role**: Centre/test management endpoints are open for simplicity. In production, these would be admin-only.
3. **Single payment per booking**: Each booking can have at most one payment record.
4. **Webhook authentication**: In production, webhooks would verify a signature/secret from the payment provider. Currently, the endpoint is open.
5. **UTC timezone**: All timestamps are stored and compared in UTC.
6. **No email verification**: User accounts are active immediately upon signup.

---

## What I Would Improve with More Time

- **Alembic migrations**: Add proper database migration versioning instead of `create_all`.
- **Redis caching**: Cache frequently accessed centre/test data with TTL-based invalidation.
- **Celery background jobs**: Process webhooks asynchronously for better throughput.
- **Admin role & RBAC**: Role-based access control for centre/test management.
- **Webhook signature verification**: HMAC-based signature validation for webhook security.
- **Appointment slot management**: Prevent double-booking of time slots at centres.
- **Email notifications**: Send booking confirmation and payment status emails.
- **API versioning strategy**: Header-based or URL-based versioning for future API changes.
- **Database connection pooling**: Fine-tune pool sizes for production load.
- **Load testing**: k6 or Locust scripts for performance benchmarking.
- **CI/CD pipeline**: GitHub Actions for automated testing, linting, and deployment.

---

## License

Built for the EVE Healthcare SDE Intern Assignment.
