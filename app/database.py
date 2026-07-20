import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load the environment variables from your .env file
load_dotenv()

# 1. Grab the Database URL from the environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Fallback in case your .env file isn't loaded or doesn't have DATABASE_URL
if not DATABASE_URL:
    raw_password = "Warlord@2208"
    safe_password = quote_plus(raw_password)
    DATABASE_URL = f"postgresql://postgres:{safe_password}@localhost:5432/identify_lms"

# 2. Database engine and session setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()