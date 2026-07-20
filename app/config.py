import os
from dotenv import load_dotenv

# Load local .env file if it exists
load_dotenv()

# Cryptographic Token security configurations
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_DEV_KEY_CHANGE_THIS_IN_PRODUCTION_1234567890")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Database configurations
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/lms_db")

# CORS Allowed Origins (Comma-separated list in .env)
# e.g., http://localhost:3000,http://127.0.0.1:3000,https://nexustech.yourplatform.com
ALLOWED_ORIGINS_STR = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8000")
ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",") if origin]