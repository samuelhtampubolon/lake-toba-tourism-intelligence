"""Command-line operational interface for administrator bootstrapping, backups, and demo data."""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import settings
from app.database import init_db, SessionLocal, backup_sqlite_database, perform_db_integrity_check
from app.models.entities import User
from app.security.auth import hash_password
from app.services.demo_data_service import generate_lake_toba_demo_dataset, seed_destinations_and_segments
from app.services.quality_service import profile_dataset_quality

def bootstrap_admin(args):
    """Create initial administrator account with secure password hashing."""
    init_db()
    with SessionLocal() as db:
        seed_destinations_and_segments(db)
        existing_admin = db.query(User).filter(User.role == "business_owner", User.is_active == True).first()
        if existing_admin and not args.force:
            print(f"[!] Active administrator '{existing_admin.username}' already exists. Use --force to add another.")
            return

        username = args.username or input("Enter administrator username [admin]: ").strip() or "admin"
        email = args.email or input(f"Enter administrator email [{username}@laketoba.local]: ").strip() or f"{username}@laketoba.local"
        
        password = args.password
        if not password:
            import getpass
            password = getpass.getpass("Enter secure password (min 8 chars): ")

        if len(password) < 8:
            print("[ERROR] Password must be at least 8 characters long.")
            sys.exit(1)

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="business_owner",
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f"[SUCCESS] Initial administrator '{username}' ({email}) successfully created.")

def seed_demo(args):
    """Generate deterministic synthetic benchmark dataset for Lake Toba."""
    init_db()
    with SessionLocal() as db:
        print("[*] Generating 2-year synthetic benchmark dataset (Seed=42)...")
        ds = generate_lake_toba_demo_dataset(db, seed=args.seed)
        print(f"[SUCCESS] Dataset '{ds.name}' generated with {ds.row_count} observations.")

def create_backup(args):
    """Hot snapshot consistent SQLite database backup."""
    backup_dir = settings.data_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest_path = str(backup_dir / f"lake_toba_backup_{timestamp}.sqlite")
    
    print(f"[*] Creating hot SQLite backup to: {dest_path}")
    backup_sqlite_database(dest_path)
    print(f"[SUCCESS] Backup successfully created at: {dest_path}")

def restore_backup(args):
    """Restore database from backup file with integrity verification."""
    backup_path = Path(args.path)
    if not backup_path.exists():
        print(f"[ERROR] Backup file not found at: {backup_path}")
        sys.exit(1)

    print(f"[*] Validating integrity of backup snapshot: {backup_path}")
    if not perform_db_integrity_check(str(backup_path)):
        print("[ERROR] Backup integrity check failed. Aborting restore.")
        sys.exit(1)

    if not args.yes:
        confirm = input(f"Are you sure you want to overwrite live database with {backup_path}? (y/N): ")
        if confirm.lower() != "y":
            print("[*] Restore cancelled.")
            return

    target_path = settings.data_path / "lake_toba.sqlite"
    import shutil
    shutil.copy2(str(backup_path), str(target_path))
    print(f"[SUCCESS] Database restored successfully from {backup_path}")

def report_environment(args):
    """Print safe environment summary without leaking secrets."""
    print("=== Lake Toba Tourism Intelligence System Report ===")
    print(f"Environment:       {settings.ENVIRONMENT}")
    print(f"Host / Port:       {settings.HOST}:{settings.PORT}")
    print(f"Data Directory:    {settings.data_path}")
    print(f"Database URL:      {settings.DATABASE_URL.split('?')[0]}")
    print(f"Python Executable: {sys.executable}")
    print(f"Python Version:    {sys.version.split()[0]}")
    print(f"Timezone:          {settings.APP_TIMEZONE}")
    print("Database Integrity: ", "OK" if perform_db_integrity_check() else "NOT FOUND / UNINITIALIZED")
    print("====================================================")

def main():
    parser = argparse.ArgumentParser(description="Lake Toba Tourism Intelligence CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # bootstrap-admin
    p_boot = subparsers.add_parser("bootstrap-admin", help="Create initial administrator user")
    p_boot.add_argument("--username", help="Admin username")
    p_boot.add_argument("--email", help="Admin email")
    p_boot.add_argument("--password", help="Admin password")
    p_boot.add_argument("--force", action="store_true", help="Force creation even if admin exists")
    p_boot.set_defaults(func=bootstrap_admin)

    # seed-demo
    p_seed = subparsers.add_parser("seed-demo", help="Generate synthetic benchmark dataset")
    p_seed.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p_seed.set_defaults(func=seed_demo)

    # backup
    p_bak = subparsers.add_parser("backup", help="Create consistent SQLite backup")
    p_bak.set_defaults(func=create_backup)

    # restore
    p_res = subparsers.add_parser("restore", help="Restore database from snapshot")
    p_res.add_argument("path", help="Path to backup sqlite file")
    p_res.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    p_res.set_defaults(func=restore_backup)

    # report-env
    p_rep = subparsers.add_parser("report-env", help="Display environment configuration")
    p_rep.set_defaults(func=report_environment)

    parsed = parser.parse_args()
    parsed.func(parsed)

if __name__ == "__main__":
    main()
