"""
Seed roles, permissions, institutions, admin user, and institutional users.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from uuid import uuid4
from api.v1.config.database import PGSyncSessionLocal
from api.v1.models.role import Role
from api.v1.models.permission import Permission
from api.v1.models.institution import Institution
from api.v1.models.user import User
from api.v1.auth.password import hash_password

db = PGSyncSessionLocal()

# ── 1. Seed Permissions ──────────────────────────────────────────────
PERMISSIONS = {
    "users:read": {"name": "Ver usuarios", "module": "users"},
    "users:create": {"name": "Crear usuarios", "module": "users"},
    "users:update": {"name": "Editar usuarios", "module": "users"},
    "users:delete": {"name": "Eliminar usuarios", "module": "users"},
    "roles:manage": {"name": "Gestionar roles", "module": "roles"},
    "beneficiaries:read": {"name": "Consultar beneficiarios", "module": "beneficiaries"},
    "beneficiaries:export": {"name": "Exportar beneficiarios", "module": "beneficiaries"},
    "databases:read": {"name": "Ver integraciones", "module": "databases"},
    "databases:manage": {"name": "Gestionar integraciones", "module": "databases"},
    "reports:read": {"name": "Ver reportes", "module": "reports"},
    "reports:advanced": {"name": "Reportes avanzados", "module": "reports"},
    "reports:create": {"name": "Crear reportes", "module": "reports"},
    "system:config": {"name": "Configuracion del sistema", "module": "system"},
    "system:monitor": {"name": "Monitoreo del sistema", "module": "system"},
    "system:audit": {"name": "Auditoria del sistema", "module": "system"},
}

perm_objs = {}
for code, data in PERMISSIONS.items():
    existing = db.query(Permission).filter(Permission.code == code).first()
    if existing:
        perm_objs[code] = existing
    else:
        p = Permission(
            code=code,
            name=data["name"],
            description=f"Permiso para {data['name'].lower()}",
            module=data["module"],
        )
        db.add(p)
        db.flush()
        perm_objs[code] = p
print(f"[OK] Permisos: {len(perm_objs)}")

# ── 2. Seed Roles ────────────────────────────────────────────────────
ROLES = {
    "ADMIN": {
        "name": "Administrador del Sistema",
        "description": "Acceso completo al sistema - gestion de usuarios, configuracion, monitoreo",
        "is_system": True,
        "permissions": list(PERMISSIONS.keys()),
    },
    "ANALYST": {
        "name": "Analista de Datos",
        "description": "Acceso a consultas y reportes completos, validacion de integraciones",
        "is_system": True,
        "permissions": [
            "beneficiaries:read",
            "beneficiaries:export",
            "databases:read",
            "reports:read",
            "reports:advanced",
            "reports:create",
        ],
    },
    "INSTITUTIONAL": {
        "name": "Usuario Institucional",
        "description": "Consultas de beneficiarios, filtros basicos, exportaciones",
        "is_system": True,
        "permissions": [
            "beneficiaries:read",
            "beneficiaries:export",
            "reports:read",
        ],
    },
}

role_objs = {}
for code, data in ROLES.items():
    existing = db.query(Role).filter(Role.code == code).first()
    if existing:
        role_objs[code] = existing
    else:
        r = Role(
            code=code,
            name=data["name"],
            description=data["description"],
            is_system=data["is_system"],
        )
        for perm_code in data["permissions"]:
            r.permissions.append(perm_objs[perm_code])
        db.add(r)
        db.flush()
        role_objs[code] = r
print(f"[OK] Roles: {list(role_objs.keys())}")

# ── 3. Seed Institutions ─────────────────────────────────────────────
INSTITUTIONS = [
    {"code": "MIDES", "name": "Ministerio de Desarrollo Social"},
    {"code": "PNUD", "name": "Programa de las Naciones Unidas para el Desarrollo"},
    {"code": "MAGA", "name": "Ministerio de Agricultura, Ganaderia y Alimentacion"},
    {"code": "FODES", "name": "Fondo de Desarrollo Social"},
]

inst_objs = {}
for inst in INSTITUTIONS:
    existing = db.query(Institution).filter(Institution.code == inst["code"]).first()
    if existing:
        inst_objs[inst["code"]] = existing
    else:
        i = Institution(code=inst["code"], name=inst["name"], is_active=True)
        db.add(i)
        db.flush()
        inst_objs[inst["code"]] = i
print(f"[OK] Instituciones: {list(inst_objs.keys())}")

# ── 4. Create Admin user ─────────────────────────────────────────────
admin_role = role_objs["ADMIN"]
mides_inst = inst_objs.get("MIDES")

existing_admin = db.query(User).filter(User.username == "admin").first()
if not existing_admin:
    admin_user = User(
        email="admin@ventanamagica.org",
        username="admin",
        password_hash=hash_password("Admin123!"),
        first_name="Administrador",
        last_name="Sistema",
        role_id=admin_role.id,
        institution_id=mides_inst.id if mides_inst else None,
        is_active=True,
        is_verified=True,
    )
    db.add(admin_user)
    print("[OK] Admin creado: admin / Admin123!")
else:
    print("[OK] Admin ya existe")

# ── 5. Create Institutional users ────────────────────────────────────
INSTITUTIONAL_USERS = [
    {
        "code": "FODES",
        "email": "fodes@ventanamagica.org",
        "username": "fodes",
        "password": "Fodes123!",
    },
    {
        "code": "MAGA",
        "email": "maga@ventanamagica.org",
        "username": "maga",
        "password": "Maga123!",
    },
    {
        "code": "MIDES",
        "email": "mides@ventanamagica.org",
        "username": "mides",
        "password": "Mides123!",
    },
]

inst_role = role_objs["INSTITUTIONAL"]
for u in INSTITUTIONAL_USERS:
    existing = db.query(User).filter(User.username == u["username"]).first()
    if not existing:
        institution = inst_objs.get(u["code"])
        user = User(
            email=u["email"],
            username=u["username"],
            password_hash=hash_password(u["password"]),
            first_name=u["code"],
            last_name="Institucional",
            role_id=inst_role.id,
            institution_id=institution.id if institution else None,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        print(f"[OK] Usuario creado: {u['username']} / {u['password']}")
    else:
        print(f"[OK] Usuario {u['username']} ya existe")

db.commit()
db.close()
print("\n=== SEED COMPLETADO ===")
print("Usuarios disponibles:")
print("  admin   / Admin123!   (ADMIN)")
print("  fodes   / Fodes123!   (INSTITUTIONAL)")
print("  maga    / Maga123!    (INSTITUTIONAL)")
print("  mides   / Mides123!   (INSTITUTIONAL)")
