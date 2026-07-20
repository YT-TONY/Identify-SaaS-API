from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])

@router.post("", response_model=schemas.CourseResponse, status_code=status.HTTP_201_CREATED)
def create_new_course(
    payload: schemas.CourseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["admin", "instructor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only administrators or instructors can create courses."
        )

    new_course = models.Course(
        title=payload.title,
        description=payload.description,
        tenant_id=current_user.tenant_id
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course


@router.get("", response_model=list[schemas.CourseResponse])
def get_tenant_courses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    courses = db.query(models.Course).filter(models.Course.tenant_id == current_user.tenant_id).all()
    return courses

# Add these endpoints to the bottom of app/routers/courses.py

@router.post("/{course_id}/lessons", response_model=schemas.LessonResponse, status_code=status.HTTP_201_CREATED)
def add_lesson_to_course(
    course_id: int,
    payload: schemas.LessonCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify course exists AND belongs to this tenant
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found in your workspace.")

    new_lesson = models.Lesson(
        title=payload.title,
        content=payload.content,
        video_url=payload.video_url,
        order=payload.order,
        course_id=course.id
    )
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    return new_lesson