import os

# In production, you will change this to a long random string using environment variables
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_COMPLEX_PASSPHRASE_FOR_IDENTIFY_LMS_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token lasts 24 hours