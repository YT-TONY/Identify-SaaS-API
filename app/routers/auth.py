from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import UserLoginRequest, TokenResponse
from app.utils import verify_password, create_access_token
import app.models as models

# 1. Create the APIRouter instance
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# 2. Use @router instead of @app!
@router.post("/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token_data = {
        "sub": user.email, 
        "user_id": user.id, 
        "role": user.role, 
        "tenant_id": user.tenant_id
    }
    access_token = create_access_token(data=token_data)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }