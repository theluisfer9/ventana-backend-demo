"""
Script to create the initial admin user.
Run this after migrations are complete.

Usage:
    python scripts/create_admin.py
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


def create_admin_user():
    if PGSyncSessionLocal is None:
        print("Error: Database not configured. Check your .env file.")
        return

    db: Session = PGSyncSessionLocal()

    try:
        # Check if admin already exists
        existing_admin = db.query(User).filter(User.username == "admin").first()
        if existing_admin:
            print("Admin user already exists.")
            return

        # Get ADMIN role
        admin_role = db.query(Role).filter(Role.code == "ADMIN").first()
        if not admin_role:
            print("Error: ADMIN role not found. Run migrations first.")
            return

        # Get MIDES institution (optional)
        mides = db.query(Institution).filter(Institution.code == "MIDES").first()

        # Create admin user
        admin_user = User(
            email="admin@ventanamagica.org",
            username="admin",
            password_hash=hash_password("Admin123!"),  # Change this password!
            first_name="Administrador",
            last_name="Sistema",
            role_id=admin_role.id,
            institution_id=mides.id if mides else None,
            is_active=True,
            is_verified=True,
        )

        db.add(admin_user)
        db.commit()

        print("=" * 50)
        print("Admin user created successfully!")
        print("=" * 50)
        print(f"Email: admin@ventanamagica.org")
        print(f"Username: admin")
        print(f"Password: Admin123!")
        print("=" * 50)
        print("IMPORTANT: Change the password after first login!")
        print("=" * 50)

    except Exception as e:
        db.rollback()
        print(f"Error creating admin user: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_admin_user()
