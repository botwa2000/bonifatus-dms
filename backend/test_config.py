# backend/test_config.py
"""
Database configuration and migration verification
"""

import sys
from sqlalchemy import create_engine, text, inspect
from typing import Tuple

# Use the same config loading as the app
from app.core.config import settings


class DatabaseValidator:
    """Validates database state and configuration"""
    
    REQUIRED_TABLES = [
        "users", "categories", "documents", 
        "system_settings", "user_settings", 
        "document_languages", "audit_logs"
    ]
    
    def __init__(self):
        self.database_url = settings.database.database_url
        self.engine = None
        self.results = []
    
    def connect(self) -> bool:
        """Test database connection"""
        try:
            self.engine = create_engine(self.database_url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self._log_success("Database connection established")
            return True
        except Exception as e:
            self._log_error(f"Database connection failed: {e}")
            return False
    
    def check_tables(self) -> bool:
        """Verify all required tables exist"""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            
            missing_tables = [t for t in self.REQUIRED_TABLES if t not in existing_tables]
            
            if missing_tables:
                self._log_error(f"Missing tables: {', '.join(missing_tables)}")
                return False
            
            self._log_success(f"All {len(self.REQUIRED_TABLES)} required tables exist")
            return True
        except Exception as e:
            self._log_error(f"Table check failed: {e}")
            return False
    
    def check_migration_version(self) -> Tuple[bool, str]:
        """Check current migration version"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                version = result.scalar()
                
                if version:
                    self._log_success(f"Migration version: {version}")
                    return True, version
                else:
                    self._log_error("No migration version found")
                    return False, None
        except Exception as e:
            self._log_error(f"Migration check failed: {e}")
            return False, None
    
    def check_system_categories(self) -> bool:
        """Verify system categories populated"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM categories WHERE is_system = true")
                )
                count = result.scalar()
                
                if count >= 5:
                    self._log_success(f"System categories: {count}/5")
                    return True
                else:
                    self._log_error(f"System categories: {count}/5 (insufficient)")
                    return False
        except Exception as e:
            self._log_error(f"System categories check failed: {e}")
            return False
    
    def check_system_settings(self) -> bool:
        """Verify system settings populated"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM system_settings")
                )
                count = result.scalar()
                
                if count >= 8:
                    self._log_success(f"System settings: {count}/8")
                    return True
                else:
                    self._log_error(f"System settings: {count}/8 (insufficient)")
                    return False
        except Exception as e:
            self._log_error(f"System settings check failed: {e}")
            return False
    
    def list_categories(self) -> None:
        """List all system categories"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT name_en, name_de, color_hex FROM categories WHERE is_system = true ORDER BY sort_order")
                )
                categories = result.fetchall()
                
                if categories:
                    print("\n" + "="*70)
                    print("SYSTEM CATEGORIES")
                    print("="*70)
                    for cat in categories:
                        print(f"• {cat[0]} / {cat[1]} ({cat[2]})")
                else:
                    print("\n⚠️  No system categories found")
        except Exception as e:
            print(f"\n❌ Failed to list categories: {e}")
    
    def list_settings(self) -> None:
        """List all system settings"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT setting_key, setting_value FROM system_settings ORDER BY category, setting_key")
                )
                settings = result.fetchall()
                
                if settings:
                    print("\n" + "="*70)
                    print("SYSTEM SETTINGS")
                    print("="*70)
                    for setting in settings:
                        print(f"• {setting[0]}: {setting[1]}")
                else:
                    print("\n⚠️  No system settings found")
        except Exception as e:
            print(f"\n❌ Failed to list settings: {e}")
    
    def _log_success(self, message: str):
        self.results.append(("✅", message))
        print(f"✅ {message}")
    
    def _log_error(self, message: str):
        self.results.append(("❌", message))
        print(f"❌ {message}")
    
    def print_summary(self):
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        passed = sum(1 for status, _ in self.results if status == "✅")
        total = len(self.results)
        
        print(f"\n{passed}/{total} checks passed")
        
        if passed == total:
            print("🎉 Database fully configured!")
        else:
            print("⚠️  Database setup incomplete")


def run_validation():
    print("="*70)
    print("DATABASE VALIDATOR")
    print("="*70)
    
    validator = DatabaseValidator()
    
    if not validator.connect():
        print("\n❌ Cannot proceed")
        sys.exit(1)
    
    validator.check_tables()
    validator.check_migration_version()
    validator.check_system_categories()
    validator.check_system_settings()
    validator.list_categories()
    validator.list_settings()
    validator.print_summary()
    
    return validator


if __name__ == "__main__":
    validator = run_validation()
    passed = sum(1 for status, _ in validator.results if status == "✅")
    total = len(validator.results)
    sys.exit(0 if passed == total else 1)