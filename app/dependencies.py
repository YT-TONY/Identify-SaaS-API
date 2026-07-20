import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt


# OAuth2PasswordBearer looks for the 'Authorization: Bearer <token>' header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET_KEY = os.getenv("SECRET_KEY", "default_fallback_secret")
ALGORITHM = "HS256"

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Decodes the JWT token and extracts the user's identity, role, and tenant_id.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        user_id: int = payload.get("user_id")
        tenant_id: int = payload.get("tenant_id")
        role: str = payload.get("role")
        email: str = payload.get("sub")
        
        if user_id is None or tenant_id is None:
            raise credentials_exception
            
        return {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "email": email
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise credentials_exception