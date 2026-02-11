"""
Script to create institutional users for FODES, MAGA, and MIDES.
Run this after migrations and initial setup.

Usage:
    python scripts/create_institutional_users.py
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from api.v1.config.database import PGSyncSessionLocal
from api.v1.models.user import User
from api.v1.models.role import Role
from api.v1.models.institution import Institution
from api.v1.auth.password import hash_password

INSTITUTIONAL_USERS = [
    {
        "code": "FODES",
        "institution_name": "Fondo de Desarrollo Social",
        "institution_description": "Fondo de Desarrollo Social - MIDES",
        "email": "fodes@ventanamagica.org",
        "username": "fodes",
        "password": "Fodes123!",
    },
    {
        "code": "MAGA",
        "institution_name": "Ministerio de Agricultura, Ganaderia y Alimentacion",
        "institution_description": "MAGA - Ministerio de Agricultura",
        "email": "maga@ventanamagica.org",
        "username": "maga",
        "password": "Maga123!",
    },
    {
        "code": "MIDES",
        "institution_name": "Ministerio de Desarrollo Social",
        "institution_description": "MIDES - Ministerio de Desarrollo Social",
        "email": "mides@ventanamagica.org",
        "username": "mides",
        "password": "Mides123!",
    },
]


def _create_user(db: Session, role: Role, inst: dict) -> None:
    """Crea un usuario institucional y su institucion si no existen."""
    code = inst["code"]

    existing = db.query(User).filter(User.email == inst["email"]).first()
    if existing:
        print(f"{code} user already exists.")
        return

    institution = db.query(Institution).filter(Institution.code == code).first()
    if not institution:
        institution = Institution(
            code=code,
            name=inst["institution_name"],
            description=inst["institution_description"],
            is_active=True,
        )
        db.add(institution)
        db.flush()
        print(f"Created {code} institution.")

    user = User(
        email=inst["email"],
        username=inst["username"],
        password_hash=hash_password(inst["password"]),
        first_name="Usuario",
        last_name=code,
        role_id=role.id,
        institution_id=institution.id,
        is_active=True,
        is_verified=True,
    )

    db.add(user)
    db.commit()

    print("=" * 50)
    print(f"{code} user created successfully!")
    print(f"  Email: {inst['email']}")
    print(f"  Username: {inst['username']}")
    print(f"  Password: {inst['password']}")
    print(f"  Role: INSTITUTIONAL")
    print(f"  Institution: {code}")
    print("=" * 50)


def create_institutional_users():
    if PGSyncSessionLocal is None:
        print("Error: Database not configured. Check your .env file.")
        return

    db: Session = PGSyncSessionLocal()

    try:
        role = db.query(Role).filter(Role.code == "INSTITUTIONAL").first()
        if not role:
            print("Error: INSTITUTIONAL role not found. Run migrations first.")
            return

        for inst in INSTITUTIONAL_USERS:
            _create_user(db, role, inst)

        print("\nIMPORTANT: Change all passwords after first login!")

    except Exception as e:
        db.rollback()
        print(f"Error creating institutional users: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_institutional_users()
