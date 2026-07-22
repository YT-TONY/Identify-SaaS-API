from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ------ TENANT & AUTH ------
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

class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: str
    tenant_id: int
    is_active: bool

    class Config:
        from_attributes = True
    
class TenantFeatures(BaseModel):
    enable_qa: bool = True
    enable_offline_downloads: bool = True
    enable_sequential_locking: bool = True
    enable_certificates: bool = False

class TenantSettingsUpdate(BaseModel):
    name: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    features: Optional[TenantFeatures] = None

class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    primary_color: str
    secondary_color: str
    features: TenantFeatures

    class Config:
        from_attributes = True

# ------ RESOURCES & LESSONS ------
class LessonResourceResponse(BaseModel):
    id: int
    title: str
    file_url: str
    file_type: str

    class Config:
        from_attributes = True

class LessonCreate(BaseModel):
    title: str
    content: Optional[str] = None
    video_url: Optional[str] = None
    order: Optional[int] = 1
    is_downloadable: Optional[bool] = False

class LessonResponse(BaseModel):
    id: int
    title: str
    content: Optional[str]
    video_url: Optional[str]
    order: int
    is_downloadable: bool
    is_locked: bool = False  # 🔒 Evaluated per student
    resources: List[LessonResourceResponse] = []

    class Config:
        from_attributes = True

# ------ MODULES & COURSES ------
class ModuleCreate(BaseModel):
    title: str
    order: Optional[int] = 1

class ModuleResponse(BaseModel):
    id: int
    title: str
    order: int
    lessons: List[LessonResponse] = []

    class Config:
        from_attributes = True

class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    is_sequential: Optional[bool] = True

class CourseResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    is_published: bool
    is_sequential: bool
    tenant_id: int
    progress_percentage: Optional[float] = 0.0  # 📊 Progress bar value
    modules: List[ModuleResponse] = []

    class Config:
        from_attributes = True

# ------ PROGRESS & ANALYTICS ------
class StudentProgressOverview(BaseModel):
    student_id: int
    student_name: str
    student_email: str
    completed_lessons: int
    total_lessons: int
    progress_percentage: float

class AdminTenantMetrics(BaseModel):
    workspace_name: str
    total_students: int
    total_courses: int
    average_tenant_completion_rate: float

# ------ Q&A ------
class AnswerCreate(BaseModel):
    content: str

class AnswerResponse(BaseModel):
    id: int
    content: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class QuestionCreate(BaseModel):
    content: str

class QuestionResponse(BaseModel):
    id: int
    content: str
    user_id: int
    created_at: datetime
    answers: List[AnswerResponse] = []

    class Config:
        from_attributes = True