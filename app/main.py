from fastapi import FastAPI, Depends, HTTPException, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional


from app.dependencies import get_current_user
from app.database import engine, Base, get_db
import app.models as models
import app.schemas as schemas
import app.config as config

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

# Initializes the Bearer token scheme extractor
security = HTTPBearer()


# --- UTILITIES & AUTH ENGINE ---

def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)


# --- THE SECURITY GATEKEEPER DEPENDENCY ---

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
        # Decode token with our secret key
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

    # Enforce complete tenant isolation by checking user and tenant context together
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


# --- PUBLIC ROUTING ENDPOINTS ---

@app.post("/api/v1/register", status_code=status.HTTP_201_CREATED)
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

    return {"message": "School workspace provisioned!", "tenant_id": new_tenant.id}


@app.post("/api/v1/login")
def login(payload: schemas.UserLoginRequest, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")


    tenant = db.query(models.Tenant).filter(models.Tenant.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Workspace/Tenant not found.")

    # 3. Create access token
    token_data = {
        "sub": user.email, 
        "user_id": user.id, 
        "role": user.role, 
        "tenant_id": tenant.id
    }
    access_token = create_access_token(data=token_data)

    # 4. Return token and branding info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_branding": {
            "school_name": tenant.name, 
            "primary_color": tenant.primary_color
        }
    }


# --- PROTECTED ROUTING ENDPOINTS (SaaS Core) ---

@app.get("/api/v1/dashboard/summary")
def get_dashboard_data(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    A locked data endpoint. Notice how it automatically has access to 
    'current_user' details because of the Depends() guard.
    """
    # Fetch data belonging ONLY to this specific tenant workspace
    tenant_workspace = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    
    return {
        "message": f"Welcome back, {current_user.full_name}!",
        "role_access": current_user.role,
        "isolated_tenant_id": current_user.tenant_id,
        "workspace_name": tenant_workspace.name,
        "mock_analytics": {
            "total_active_students": 142,
            "published_courses": 8,
            "server_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

# --- PROTECTED COURSE ENDPOINTS ---

@app.post("/api/v1/courses", response_model=schemas.CourseResponse, status_code=status.HTTP_201_CREATED)
def create_new_course(
    payload: schemas.CourseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new course. The system automatically tags the course 
    with the logged-in user's school ID to preserve strict isolation.
    """
    # Optional: You could add a check here to ensure only 'admin' or 'instructor' roles can create courses
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only administrators or instructors can create courses."
        )

    new_course = models.Course(
        title=payload.title,
        description=payload.description,
        tenant_id=current_user.tenant_id  # Injected automatically from token!
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@app.get("/api/v1/courses", response_model=list[schemas.CourseResponse])
def get_tenant_courses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches all courses belonging ONLY to the logged-in user's specific school workspace.
    """
    # Strict filter query ensures zero cross-tenant data leaks
    courses = db.query(models.Course).filter(models.Course.tenant_id == current_user.tenant_id).all()
    return courses

def get_active_tenant(
    request: Request,
    x_tenant_slug: Optional[str] = Header(None, alias="X-Tenant-Slug"),
    db: Session = Depends(get_db)
) -> models.Tenant:
    """
    SaaS Tenant Boundary Resolver. Detects the school context 
    via an 'X-Tenant-Slug' HTTP Header OR automatically parses the 
    host subdomain (e.g. 'alpha.yourplatform.com').
    """
    tenant_slug = None

    # Option A: Check for the developer-friendly HTTP Header first
    if x_tenant_slug:
        tenant_slug = x_tenant_slug.lower().strip()

    # Option B: Fallback to reading the host subdomain (for white-labeled web domains)
    else:
        host = request.url.hostname or ""
        parts = host.split(".")
        
        # If host is 'schoolname.localhost' or 'schoolname.lms.com'
        if len(parts) > 1:
            subdomain = parts[0]
            # Skip common non-tenant subdomains
            if subdomain not in ["www", "api", "admin", "localhost"]:
                tenant_slug = subdomain.lower().strip()

    if not tenant_slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine tenant context. Please provide an 'X-Tenant-Slug' header or access via a tenant subdomain."
        )

    # Locate the Tenant database entry
    tenant = db.query(models.Tenant).filter(models.Tenant.slug == tenant_slug).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The requested school workspace does not exist."
        )
        
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This school workspace has been suspended."
        )

    return tenant

@app.post("/api/v1/login")
def login(
    payload: schemas.UserLoginRequest, 
    tenant: models.Tenant = Depends(get_active_tenant), # Injected automatically!
    db: Session = Depends(get_db)
):
    """
    Logs in a user. Notice we don't ask for a tenant_slug in the JSON.
    It is resolved dynamically from your request context.
    """
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

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "tenant_branding": {
            "school_name": tenant.name, 
            "primary_color": tenant.primary_color,
            "logo_url": tenant.logo_url
        }
    }


@app.get("/me")
def get_my_profile(current_user: dict = Depends(get_current_user)):
    """
    Test endpoint to verify that our JWT token works.
    """
    return {
        "message": "Token is valid!",
        "user_details": current_user
    }