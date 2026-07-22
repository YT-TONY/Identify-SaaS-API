from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_active_tenant
from app.utils import hash_password, verify_password, create_access_token
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1", tags=["Authentication & Onboarding"])

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_tenant(payload: schemas.TenantOnboardingRequest, db: Session = Depends(get_db)):
    existing_tenant = db.query(models.Tenant).filter(models.Tenant.slug == payload.tenant.slug).first()
    if existing_tenant:
        raise HTTPException(status_code=400, detail="This URL slug is already taken.")

    existing_user = db.query(models.User).filter(models.User.email == payload.admin.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="An administrator with this email already exists.")

    new_tenant = models.Tenant(
        name=payload.tenant.name,
        slug=payload.tenant.slug.lower().strip(),
        primary_color=payload.tenant.primary_color,
        secondary_color=payload.tenant.secondary_color
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)

    hashed_pwd = hash_password(payload.admin.password)
    new_admin = models.User(
        email=payload.admin.email,
        hashed_password=hashed_pwd,
        full_name=payload.admin.full_name,
        role="admin",
        tenant_id=new_tenant.id
    )
    db.add(new_admin)
    db.commit()

    return {"message": "Workspace provisioned!", "tenant_id": new_tenant.id}


@router.post("/login")
def login(
    payload: schemas.UserLoginRequest, 
    tenant: models.Tenant = Depends(get_active_tenant),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(
        models.User.email == payload.email, 
        models.User.tenant_id == tenant.id
    ).first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password."
        )

    token_data = {
        "sub": user.email, 
        "user_id": user.id, 
        "role": user.role, 
        "tenant_id": tenant.id
    }
    access_token = create_access_token(data=token_data)

   # inside app/routers/auth.py login endpoint:
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_config": {
            "school_name": tenant.name, 
            "primary_color": tenant.primary_color,
            "secondary_color": tenant.secondary_color,
            "features": tenant.features  
        }
    }
