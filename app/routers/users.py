from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.dependencies import get_current_user
from app.utils import hash_password
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/users", tags=["User & Dashboard"])

# 1. Tenant Admin creates users (instructors, members, staff) for their tenant
@router.post("", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def create_tenant_user(
    payload: schemas.UserCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only Admin or Instructor can create users inside this tenant
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can add users to this workspace."
        )

    # Check if email is already taken
    existing_user = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists.")

    new_user = models.User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role if payload.role else "student",
        tenant_id=current_user.tenant_id  # 🔒 Locked to admin's tenant workspace automatically
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.get("/me")
def get_my_profile(current_user: models.User = Depends(get_current_user)):
    """
    Test endpoint to verify that JWT token works.
    """
    return {
        "message": "Token is valid!",
        "user_details": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "tenant_id": current_user.tenant_id
        }
    }

@router.get("/api/v1/dashboard/summary")
def get_dashboard_data(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    tenant_workspace = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    
    return {
        "message": f"Welcome back, {current_user.full_name}!",
        "role_access": current_user.role,
        "isolated_tenant_id": current_user.tenant_id,
        "workspace_name": tenant_workspace.name if tenant_workspace else "N/A",
        "mock_analytics": {
            "total_active_students": 142,
            "published_courses": 8,
            "server_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }