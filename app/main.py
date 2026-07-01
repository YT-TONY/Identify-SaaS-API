from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone

from app.database import engine, Base, get_db
import app.models as models
import app.schemas as schemas
import app.config as config

# Ensure database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Identify LMS Core API")

# Password Utilities
def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# JWT Token Engine
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


@app.post("/api/v1/register", status_code=status.HTTP_201_CREATED)
def register_tenant(payload: schemas.TenantOnboardingRequest, db: Session = Depends(get_db)):
    
    # 1. Check if the school URL slug is already taken
    existing_tenant = db.query(models.Tenant).filter(models.Tenant.slug == payload.tenant.slug).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This URL slug is already taken by another school."
        )

    # 2. Check if the administrator email is already registered
    existing_user = db.query(models.User).filter(models.User.email == payload.admin.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An administrator with this email address already exists."
        )

    # 3. Create the School/Tenant environment
    new_tenant = models.Tenant(
        name=payload.tenant.name,
        slug=payload.tenant.slug.lower().strip(),
        primary_color=payload.tenant.primary_color,
        secondary_color=payload.tenant.secondary_color
    )
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant) # This gives us access to the auto-generated new_tenant.id

    # 4. Create the Tenant Owner (Admin User) linked to the new school id
    hashed_pwd = hash_password(payload.admin.password)
    new_admin = models.User(
        email=payload.admin.email,
        hashed_password=hashed_pwd,
        full_name=payload.admin.full_name,
        role="admin", # Hardcoded to admin for registration
        tenant_id=new_tenant.id
    )
    db.add(new_admin)
    db.commit()

    return {
        "message": "School platform and admin user successfully provisioned!",
        "tenant_id": new_tenant.id,
        "school_name": new_tenant.name,
        "admin_email": new_admin.email
    }
 
@app.post("/api/v1/login")
def login(payload: schemas.UserLoginRequest, db: Session = Depends(get_db)):
    
    # 1. Verify the school environment exists
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == payload.tenant_slug.lower().strip()).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="School platform workspace not found."
        )

    # 2. Find the user, explicitly making sure they belong to THIS specific tenant
    user = db.query(models.User).filter(
        models.User.email == payload.email,
        models.User.tenant_id == tenant.id
    ).first()
    
    # 3. Securely cross-check passwords
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password configuration for this school."
        )

    # 4. Check if the workspace or account has been suspended
    if not tenant.is_active or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account or school space has been deactivated."
        )

    # 5. Pack the payload into the signed secure JWT token
    token_data = {
        "sub": user.email,
        "user_id": user.id,
        "role": user.role,
        "tenant_id": tenant.id,
        "tenant_slug": tenant.slug
    }
    
    access_token = create_access_token(data=token_data)

    # 6. Return token along with the custom UI branding data for Flutter
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "full_name": user.full_name,
            "role": user.role
        },
        "tenant_branding": {
            "school_name": tenant.name,
            "primary_color": tenant.primary_color,
            "secondary_color": tenant.secondary_color,
            "logo_url": tenant.logo_url
        }
    }
