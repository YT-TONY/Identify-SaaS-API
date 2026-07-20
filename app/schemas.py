from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

# ------TENANT & ONBOARDING SCHEMAS------
class TenantCreate(BaseModel):
    name: str = Field(..., example="Dave's Coding Academy")
    slug: str = Field(..., example="davecode")
    primary_color: Optional[str] = "#000000"
    secondary_color: Optional[str] = "#FFFFFF"

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str

class TenantOnboardingRequest(BaseModel):
    tenant: TenantCreate
    admin: AdminUserCreate


# ------AUTH SCHEMAS------
class UserLoginRequest(BaseModel):
    email: EmailStr = Field(..., example="admin@davecode.com")
    password: str = Field(..., min_length=6)


# ------USER SCHEMAS------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=6)
    role: Optional[str] = "student"

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    tenant_id: Optional[int] = None
    is_active: bool = True

    class Config:
        from_attributes = True


# ------LESSON SCHEMAS------
class LessonCreate(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: Optional[int] = 1

class LessonResponse(LessonCreate):
    id: int
    course_id: int

    class Config:
        from_attributes = True


# ------COURSE SCHEMAS------
class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None

class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    is_published: bool = True
    tenant_id: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True


# ------ENROLLMENT SCHEMAS------
class EnrollmentCreate(BaseModel):
    course_id: int

class EnrollmentResponse(BaseModel):
    id: int
    user_id: int
    course_id: int
    tenant_id: int

    class Config:
        from_attributes = True