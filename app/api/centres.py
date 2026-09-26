"""Diagnostic Centres & Tests API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.centre import DiagnosticCentre
from app.models.test import CentreTest, DiagnosticTest
from app.schemas.centre import (
    CentreCreateRequest,
    CentreListResponse,
    CentreResponse,
    TestInCentreResponse,
)
from app.schemas.test import (
    CentreTestCreateRequest,
    CentreTestResponse,
    TestCreateRequest,
    TestListResponse,
    TestResponse,
)

settings = get_settings()
router = APIRouter(prefix="/centres", tags=["Diagnostic Centres & Tests"])


# ── Diagnostic Centres ───────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=CentreResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a diagnostic centre",
)
def create_centre(data: CentreCreateRequest, db: Session = Depends(get_db)):
    """Create a new diagnostic centre."""
    centre = DiagnosticCentre(
        name=data.name,
        location=data.location,
        address=data.address,
        phone=data.phone,
    )
    db.add(centre)
    db.commit()
    db.refresh(centre)

    return _build_centre_response(centre)


@router.get(
    "/",
    response_model=CentreListResponse,
    summary="List diagnostic centres",
    description="Retrieve a paginated list of active diagnostic centres.",
)
def list_centres(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    location: str | None = Query(None, description="Filter by location"),
    db: Session = Depends(get_db),
):
    """List diagnostic centres with optional location filter and pagination."""
    query = db.query(DiagnosticCentre).filter(DiagnosticCentre.is_active.is_(True))

    if location:
        query = query.filter(DiagnosticCentre.location.ilike(f"%{location}%"))

    total = query.count()
    centres = (
        query.order_by(DiagnosticCentre.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return CentreListResponse(
        centres=[_build_centre_response(c) for c in centres],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{centre_id}",
    response_model=CentreResponse,
    summary="Get diagnostic centre details",
)
def get_centre(centre_id: UUID, db: Session = Depends(get_db)):
    """Retrieve a single diagnostic centre with its available tests."""
    centre = (
        db.query(DiagnosticCentre)
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if not centre:
        raise NotFoundException(detail="Diagnostic centre not found")

    return _build_centre_response(centre)


# ── Diagnostic Tests ─────────────────────────────────────────────────────────


@router.post(
    "/tests",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a diagnostic test",
)
def create_test(data: TestCreateRequest, db: Session = Depends(get_db)):
    """Create a new diagnostic test type."""
    test = DiagnosticTest(
        name=data.name,
        description=data.description,
        category=data.category,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return TestResponse.model_validate(test)


@router.get(
    "/tests/all",
    response_model=TestListResponse,
    summary="List all diagnostic tests",
)
def list_tests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
):
    """List all diagnostic tests with optional category filter."""
    query = db.query(DiagnosticTest)

    if category:
        query = query.filter(DiagnosticTest.category.ilike(f"%{category}%"))

    total = query.count()
    tests = (
        query.order_by(DiagnosticTest.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return TestListResponse(
        tests=[TestResponse.model_validate(t) for t in tests],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Centre-Test Linking (pricing) ────────────────────────────────────────────


@router.post(
    "/tests/link",
    response_model=CentreTestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a test to a centre with pricing",
)
def link_test_to_centre(
    data: CentreTestCreateRequest, db: Session = Depends(get_db)
):
    """Associate a diagnostic test with a centre and set its price."""
    # Validate centre
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == data.centre_id).first()
    if not centre:
        raise NotFoundException(detail="Diagnostic centre not found")

    # Validate test
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == data.test_id).first()
    if not test:
        raise NotFoundException(detail="Diagnostic test not found")

    # Check duplicate
    existing = (
        db.query(CentreTest)
        .filter(CentreTest.centre_id == data.centre_id, CentreTest.test_id == data.test_id)
        .first()
    )
    if existing:
        from app.core.exceptions import ConflictException
        raise ConflictException(detail="This test is already linked to this centre")

    centre_test = CentreTest(
        centre_id=data.centre_id,
        test_id=data.test_id,
        price=data.price,
    )
    db.add(centre_test)
    db.commit()
    db.refresh(centre_test)

    return CentreTestResponse(
        id=centre_test.id,
        centre_id=centre.id,
        centre_name=centre.name,
        test_id=test.id,
        test_name=test.name,
        price=centre_test.price,
        is_available=centre_test.is_available,
    )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_centre_response(centre: DiagnosticCentre) -> CentreResponse:
    """Build a CentreResponse with nested test information."""
    tests = []
    for ct in centre.centre_tests:
        if ct.is_available:
            tests.append(
                TestInCentreResponse(
                    centre_test_id=ct.id,
                    test_id=ct.test.id,
                    test_name=ct.test.name,
                    category=ct.test.category,
                    price=ct.price,
                    is_available=ct.is_available,
                )
            )

    return CentreResponse(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        address=centre.address,
        phone=centre.phone,
        is_active=centre.is_active,
        created_at=centre.created_at,
        tests=tests,
    )
