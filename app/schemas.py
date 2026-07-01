from pydantic import BaseModel, EmailStr, Field
from typing import Optional

# Data needed to create a School/Tenant
class TenantCreate(BaseModel):
    name: str = Field(..., example="Dave's Coding Academy")
    slug: str = Field(..., example="davecode")
    primary_color: Optional[str] = "#000000"
    secondary_color: Optional[str] = "#FFFFFF"

# Data needed to create the Admin User
class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str

# The combined onboarding request body
class TenantOnboardingRequest(BaseModel):
    tenant: TenantCreate
    admin: AdminUserCreate

# Add this to the bottom of app/schemas.py
class UserLoginRequest(BaseModel):
    tenant_slug: str = Field(..., example="davecode")
    email: EmailStr = Field(..., example="admin@davecode.com")
    password: str = Field(..., min_length=6)