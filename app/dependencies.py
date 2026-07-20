from fastapi import Depends, HTTPException, status, Request, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from typing import Optional

from app.database import get_db
import app.models as models
import app.config as config

security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db: Session = Depends(get_db)
) -> models.User:
    """
    Protects routes. Decodes the JWT token, extracts user info, 
    and validates everything against the database.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email: str = payload.get("sub")
        tenant_id: int = payload.get("tenant_id")
        
        if email is None or tenant_id is None:
            raise credentials_exception
            
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Your session has expired. Please log in again."
        )
    except jwt.InvalidTokenError:
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.email == email, 
        models.User.tenant_id == tenant_id
    ).first()
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Your user account is suspended."
        )
        
    return user


def get_active_tenant(
    request: Request,
    x_tenant_slug: Optional[str] = Header(None, alias="X-Tenant-Slug"),
    db: Session = Depends(get_db)
) -> models.Tenant:
    """
    SaaS Tenant Boundary Resolver. Detects the tenant context 
    via an 'X-Tenant-Slug' HTTP Header OR host subdomain.
    """
    tenant_slug = None

    if x_tenant_slug:
        tenant_slug = x_tenant_slug.lower().strip()
    else:
        host = request.url.hostname or ""
        parts = host.split(".")
        if len(parts) > 1:
            subdomain = parts[0]
            if subdomain not in ["www", "api", "admin", "localhost"]:
                tenant_slug = subdomain.lower().strip()

    if not tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine tenant context. Please provide an 'X-Tenant-Slug' header or access via a tenant subdomain."
        )

    tenant = db.query(models.Tenant).filter(models.Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested workspace does not exist."
        )
        
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This workspace has been suspended."
        )

    return tenant