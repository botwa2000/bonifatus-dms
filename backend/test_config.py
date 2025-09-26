# backend/test_config.py
"""
Bonifatus DMS - Environment Variables Configuration Test
Validates all required environment variables are properly set
Zero tolerance for missing configuration - production standards
"""

import os
import sys
from typing import Dict, List, Tuple


class EnvironmentValidator:
    """Validates all required environment variables for production deployment"""
    
    # All required environment variables mapped to their configuration sections
    REQUIRED_VARIABLES = {
        # Database Configuration
        "DATABASE_URL": "Database connection URL",
        "DATABASE_POOL_SIZE": "Connection pool size", 
        "DATABASE_POOL_RECYCLE": "Pool recycle time",
        "DATABASE_ECHO": "Enable SQL query logging",
        "DATABASE_POOL_PRE_PING": "Enable connection health checks",
        "DATABASE_CONNECT_TIMEOUT": "Connection timeout",
        
        # Google Services Configuration
        "GOOGLE_CLIENT_ID": "Google OAuth client ID",
        "GOOGLE_CLIENT_SECRET": "Google OAuth client secret", 
        "GOOGLE_REDIRECT_URI": "OAuth redirect URI",
        "GOOGLE_VISION_ENABLED": "Enable Google Vision OCR",
        "GOOGLE_OAUTH_ISSUERS": "Valid OAuth issuers",
        "GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY": "Google Drive service account key",
        "GOOGLE_DRIVE_FOLDER_NAME": "Google Drive folder name",
        "GCP_PROJECT": "Google Cloud Project ID",
        
        # Security Configuration
        "SECURITY_SECRET_KEY": "JWT secret key",
        "ALGORITHM": "JWT algorithm", 
        "ACCESS_TOKEN_EXPIRE_MINUTES": "JWT expiration",
        "REFRESH_TOKEN_EXPIRE_DAYS": "Refresh token expiration",
        "DEFAULT_USER_TIER": "Default user tier",
        "ADMIN_EMAILS": "Admin email list",
        
        # Application Configuration
        "APP_ENVIRONMENT": "Environment",
        "APP_DEBUG_MODE": "Enable debug mode",
        "APP_CORS_ORIGINS": "CORS origins", 
        "APP_HOST": "Application host",
        "APP_PORT": "Application port",
        "APP_TITLE": "Application title",
        "APP_DESCRIPTION": "Application description", 
        "APP_VERSION": "Application version"
    }
    
    def __init__(self):
        self.missing_variables: List[str] = []
        self.set_variables: Dict[str, str] = {}
        self.validation_errors: List[str] = []
        
    def check_environment_variables(self) -> bool:
        """Check if all required environment variables are set"""
        print("=== Environment Variables Validation ===")
        
        for var_name, description in self.REQUIRED_VARIABLES.items():
            value = os.getenv(var_name)
            
            if value is None or value.strip() == "":
                self.missing_variables.append(var_name)
                print(f"❌ {var_name}: NOT SET ({description})")
            else:
                self.set_variables[var_name] = value
                # Show partial value for security (don't expose secrets)
                display_value = self._mask_sensitive_value(var_name, value)
                print(f"✅ {var_name}: {display_value} ({description})")
        
        total_vars = len(self.REQUIRED_VARIABLES)
        set_vars = len(self.set_variables)
        
        print(f"\n📊 Environment Variables Status: {set_vars}/{total_vars} configured")
        
        if self.missing_variables:
            print(f"❌ Missing {len(self.missing_variables)} required variables:")
            for var in self.missing_variables:
                print(f"   - {var}")
            return False
        
        print("✅ All required environment variables are set")
        return True
    
    def _mask_sensitive_value(self, var_name: str, value: str) -> str:
        """Mask sensitive values in output"""
        sensitive_vars = [
            "SECURITY_SECRET_KEY", "GOOGLE_CLIENT_SECRET", 
            "DATABASE_URL", "GOOGLE_DRIVE_SERVICE_ACCOUNT_KEY"
        ]
        
        if var_name in sensitive_vars:
            if len(value) > 8:
                return f"{value[:4]}...{value[-4:]}"
            else:
                return "***"
        
        # Show full value for non-sensitive vars
        return value
    
    def test_configuration_loading(self) -> bool:
        """Test that Pydantic configuration loads successfully"""
        print("\n=== Configuration Loading Test ===")
        
        try:
            from app.core.config import settings
            print("✅ Configuration loaded successfully")
            
            # Test each configuration section
            sections_status = []
            
            # App settings
            try:
                app_config = settings.app
                print(f"✅ App Config: {app_config.app_title} v{app_config.app_version}")
                sections_status.append(("App", True))
            except Exception as e:
                print(f"❌ App Config Failed: {e}")
                sections_status.append(("App", False))
            
            # Database settings  
            try:
                db_config = settings.database
                print(f"✅ Database Config: Pool size {db_config.database_pool_size}")
                sections_status.append(("Database", True))
            except Exception as e:
                print(f"❌ Database Config Failed: {e}")
                sections_status.append(("Database", False))
            
            # Google settings
            try:
                google_config = settings.google
                client_id_preview = google_config.google_client_id[:20] + "..." if len(google_config.google_client_id) > 20 else google_config.google_client_id
                print(f"✅ Google Config: Client ID {client_id_preview}")
                sections_status.append(("Google", True))
            except Exception as e:
                print(f"❌ Google Config Failed: {e}")
                sections_status.append(("Google", False))
            
            # Security settings
            try:
                security_config = settings.security
                print(f"✅ Security Config: Algorithm {security_config.algorithm}")
                sections_status.append(("Security", True))
            except Exception as e:
                print(f"❌ Security Config Failed: {e}")
                sections_status.append(("Security", False))
            
            # Check if all sections loaded
            failed_sections = [name for name, status in sections_status if not status]
            if failed_sections:
                print(f"❌ Configuration sections failed: {', '.join(failed_sections)}")
                return False
            
            print("✅ All configuration sections loaded successfully")
            return True
            
        except Exception as e:
            print(f"❌ Configuration loading failed: {e}")
            self.validation_errors.append(f"Configuration loading error: {e}")
            return False
    
    def test_configuration_properties(self) -> bool:
        """Test configuration derived properties"""
        print("\n=== Configuration Properties Test ===")
        
        try:
            from app.core.config import settings
            
            # Test environment detection
            print(f"✅ Environment Detection: {settings.app.app_environment}")
            print(f"   - is_production: {settings.is_production}")
            print(f"   - is_development: {settings.is_development}")
            print(f"   - is_staging: {settings.is_staging}")
            
            # Test list parsing
            admin_emails = settings.admin_email_list
            cors_origins = settings.cors_origins_list
            oauth_issuers = settings.google_oauth_issuer_list
            
            print(f"✅ Admin Emails: {len(admin_emails)} configured")
            print(f"✅ CORS Origins: {len(cors_origins)} configured")
            print(f"✅ OAuth Issuers: {len(oauth_issuers)} configured")
            
            return True
            
        except Exception as e:
            print(f"❌ Configuration properties test failed: {e}")
            self.validation_errors.append(f"Configuration properties error: {e}")
            return False
    
    def test_application_startup(self) -> bool:
        """Test that FastAPI application can be created"""
        print("\n=== Application Startup Test ===")
        
        try:
            from app.main import app
            print(f"✅ FastAPI Application Created: {app.title} v{app.version}")
            return True
        except Exception as e:
            print(f"❌ Application startup failed: {e}")
            self.validation_errors.append(f"Application startup error: {e}")
            return False
    
    def run_full_validation(self) -> Tuple[bool, List[str]]:
        """Run complete validation suite"""
        print("🧪 Bonifatus DMS - Complete Environment Validation\n")
        
        tests = [
            ("Environment Variables", self.check_environment_variables),
            ("Configuration Loading", self.test_configuration_loading), 
            ("Configuration Properties", self.test_configuration_properties),
            ("Application Startup", self.test_application_startup)
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                success = test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"❌ {test_name} Test Error: {e}")
                results.append((test_name, False))
                self.validation_errors.append(f"{test_name}: {e}")
        
        # Summary
        print("\n" + "="*50)
        print("📊 VALIDATION SUMMARY")
        print("="*50)
        
        passed_tests = 0
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{test_name}: {status}")
            if success:
                passed_tests += 1
        
        total_tests = len(results)
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Ready for deployment!")
            return True, []
        else:
            print("💥 VALIDATION FAILED - Fix issues before deployment")
            print("\nIssues to resolve:")
            if self.missing_variables:
                print("Missing environment variables:")
                for var in self.missing_variables:
                    print(f"  - {var}")
            if self.validation_errors:
                print("Configuration errors:")
                for error in self.validation_errors:
                    print(f"  - {error}")
            
            return False, self.missing_variables + self.validation_errors


def main():
    """Main validation execution"""
    validator = EnvironmentValidator()
    success, errors = validator.run_full_validation()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()