from app.database import engine, Base
# Import all your models so SQLAlchemy knows which tables to reset
import app.models 

print("🗑️ Dropping all tables from database...")
Base.metadata.drop_all(bind=engine)

print("✨ Recreating fresh, empty tables...")
Base.metadata.create_all(bind=engine)

print("✅ Database successfully reset!")