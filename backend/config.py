import os
import json
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# App environment
TESTING = os.getenv("TESTING", "False").lower() in ("true", "1", "t", "yes", "y")

# Database configuration
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hospital_resource_intelligence")

if TESTING:
    # Use file-based SQLite database for test suites to share connection context
    DATABASE_URL = "sqlite:///test.db"
else:
    # PostgreSQL production URL
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# CORS Configuration
raw_origins = os.getenv("CORS_ORIGINS", '["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]')
try:
    CORS_ORIGINS = json.loads(raw_origins)
except Exception:
    CORS_ORIGINS = ["http://localhost:3000"]

# JWT Configuration settings
JWT_SECRET = os.getenv("JWT_SECRET", "supersecretkeychangeinproduction")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Default Admin Credential settings
DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "AdminPassword123")

