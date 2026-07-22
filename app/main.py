from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
import app.config as config

from app.routers import auth, tenants, users, courses, enrollments, progress, qa

Base.metadata.create_all(bind=engine)

app = FastAPI(title="White-Label SaaS Core Engine")

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
app.include_router(enrollments.router)
app.include_router(progress.router)
app.include_router(qa.router)
app.include_router(tenants.router)

@app.get("/")
def health_check():
    return {"status": "online", "message": "Multi-Tenant SaaS Engine running cleanly!"}