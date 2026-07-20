from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
import app.config as config

# Import modularized routers
from app.routers import auth, users, courses
from app.routers import auth, users, courses, enrollments

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="White-Label LMS Core API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(enrollments.router) # 👈 Add this line!

@app.get("/")
def health_check():
    return {"status": "online", "message": "White-Label LMS Core API is up and running!"}