"""Seed the database with sample diagnostic centres and tests."""

from decimal import Decimal

from app.database import SessionLocal
from app.models.centre import DiagnosticCentre
from app.models.test import CentreTest, DiagnosticTest

CENTRES = [
    {
        "name": "HealthFirst Diagnostics",
        "location": "Mumbai",
        "address": "123 Marine Drive, Mumbai, Maharashtra 400001",
        "phone": "+91-22-12345678",
    },
    {
        "name": "MedScan Labs",
        "location": "Delhi",
        "address": "45 Connaught Place, New Delhi 110001",
        "phone": "+91-11-87654321",
    },
    {
        "name": "CityLab Diagnostics",
        "location": "Bangalore",
        "address": "78 MG Road, Bangalore, Karnataka 560001",
        "phone": "+91-80-11223344",
    },
]

TESTS = [
    {
        "name": "Complete Blood Count (CBC)",
        "description": "Measures various components of blood including RBC, WBC, and platelets.",
        "category": "Hematology",
    },
    {
        "name": "Lipid Profile",
        "description": "Measures cholesterol and triglyceride levels in the blood.",
        "category": "Biochemistry",
    },
    {
        "name": "Thyroid Function Test (TFT)",
        "description": "Measures TSH, T3, and T4 levels to assess thyroid function.",
        "category": "Endocrinology",
    },
    {
        "name": "Liver Function Test (LFT)",
        "description": "Evaluates liver health by measuring enzymes and proteins.",
        "category": "Biochemistry",
    },
    {
        "name": "MRI Brain",
        "description": "Magnetic resonance imaging of the brain for detailed structural analysis.",
        "category": "Radiology",
    },
    {
        "name": "Chest X-Ray",
        "description": "Radiographic examination of the chest.",
        "category": "Radiology",
    },
    {
        "name": "HbA1c (Glycated Hemoglobin)",
        "description": "Measures average blood sugar over the past 2-3 months.",
        "category": "Endocrinology",
    },
    {
        "name": "Vitamin D Test",
        "description": "Measures 25-hydroxy vitamin D levels in the blood.",
        "category": "Biochemistry",
    },
]

# Price matrix: (centre_index, test_index) -> price
# Each centre offers tests at slightly different prices
PRICING = {
    (0, 0): Decimal("450.00"),
    (0, 1): Decimal("800.00"),
    (0, 2): Decimal("650.00"),
    (0, 3): Decimal("700.00"),
    (0, 4): Decimal("8500.00"),
    (0, 5): Decimal("350.00"),
    (0, 6): Decimal("550.00"),
    (0, 7): Decimal("900.00"),
    (1, 0): Decimal("400.00"),
    (1, 1): Decimal("750.00"),
    (1, 2): Decimal("600.00"),
    (1, 3): Decimal("680.00"),
    (1, 4): Decimal("9000.00"),
    (1, 5): Decimal("300.00"),
    (1, 6): Decimal("500.00"),
    (2, 0): Decimal("500.00"),
    (2, 1): Decimal("850.00"),
    (2, 2): Decimal("700.00"),
    (2, 4): Decimal("7500.00"),
    (2, 5): Decimal("380.00"),
    (2, 7): Decimal("950.00"),
}


def seed():
    """Populate the database with sample data."""
    db = SessionLocal()

    try:
        # Skip if data already exists
        if db.query(DiagnosticCentre).first():
            print("⚠️  Database already contains data. Skipping seed.")
            return

        # Create centres
        centre_objs = []
        for c in CENTRES:
            centre = DiagnosticCentre(**c)
            db.add(centre)
            centre_objs.append(centre)
        db.flush()

        # Create tests
        test_objs = []
        for t in TESTS:
            test = DiagnosticTest(**t)
            db.add(test)
            test_objs.append(test)
        db.flush()

        # Link centres to tests with pricing
        for (ci, ti), price in PRICING.items():
            ct = CentreTest(
                centre_id=centre_objs[ci].id,
                test_id=test_objs[ti].id,
                price=price,
            )
            db.add(ct)

        db.commit()
        print("✅ Database seeded successfully!")
        print(f"   → {len(centre_objs)} centres")
        print(f"   → {len(test_objs)} tests")
        print(f"   → {len(PRICING)} centre-test links")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    # Import models to ensure tables exist
    from app.database import Base, engine
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    seed()
