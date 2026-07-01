import os
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. Define your database connection URL

raw_password = "Warlord@2208"
safe_password = quote_plus(raw_password)  # URL encode the '@' character
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql://postgres:{safe_password}@localhost:5432/identify_lms"
)

# 2. Create the SQLAlchemy Engine (the actual bridge to the database)
engine = create_engine(DATABASE_URL)

# 3. Create a Session factory (creates temporary conversations with the DB)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create the Base class that our models (Tenants, Users) will inherit from
Base = declarative_base()

# 5. Database Dependency (Crucial for FastAPI)
# This opens a connection when a user visits a page and closes it automatically when they leave.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()