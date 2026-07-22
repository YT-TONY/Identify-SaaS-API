from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/courses", tags=["Courses & Content Delivery"])

@router.post("", response_model=schemas.CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: schemas.CourseCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only admins or teachers can create courses.")

    new_course = models.Course(
        title=payload.title,
        description=payload.description,
        is_sequential=payload.is_sequential,
        tenant_id=current_user.tenant_id
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@router.post("/{course_id}/modules", response_model=schemas.ModuleResponse, status_code=status.HTTP_201_CREATED)
def create_module(
    course_id: int,
    payload: schemas.ModuleCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    new_module = models.Module(title=payload.title, order=payload.order, course_id=course.id)
    db.add(new_module)
    db.commit()
    db.refresh(new_module)
    return new_module

@router.post("/modules/{module_id}/lessons", response_model=schemas.LessonResponse, status_code=status.HTTP_201_CREATED)
def create_lesson(
    module_id: int,
    payload: schemas.LessonCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    module = db.query(models.Module).join(models.Course).filter(
        models.Module.id == module_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found.")

    new_lesson = models.Lesson(
        title=payload.title,
        content=payload.content,
        video_url=payload.video_url,
        order=payload.order,
        is_downloadable=payload.is_downloadable,
        module_id=module.id
    )
    db.add(new_lesson)
    db.commit()
    db.refresh(new_lesson)
    return new_lesson

@router.get("/{course_id}", response_model=schemas.CourseResponse)
def get_course_details_with_locks(
    course_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # Get all completed lesson IDs for this student
    completed_ids = set(
        c.lesson_id for c in db.query(models.LessonCompletion).filter(
            models.LessonCompletion.user_id == current_user.id,
            models.LessonCompletion.tenant_id == current_user.tenant_id
        ).all()
    )

    all_lessons = []
    for module in course.modules:
        module.lessons.sort(key=lambda x: x.order)
        all_lessons.extend(module.lessons)

    total_lessons = len(all_lessons)
    completed_count = 0
    previous_completed = True

    for lesson in all_lessons:
        if lesson.id in completed_ids:
            completed_count += 1
            lesson.is_locked = False
            previous_completed = True
        else:
            if course.is_sequential:
                lesson.is_locked = not previous_completed
                previous_completed = False
            else:
                lesson.is_locked = False

    course.progress_percentage = (completed_count / total_lessons * 100) if total_lessons > 0 else 0.0
    return course

# 🎬 Netflix-Style Stream / Offline Download Link Endpoint
@router.get("/lessons/{lesson_id}/offline-stream-token")
def get_offline_stream_token(
    lesson_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lesson = db.query(models.Lesson).join(models.Module).join(models.Course).filter(
        models.Lesson.id == lesson_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found.")

    if not lesson.is_downloadable:
        raise HTTPException(status_code=403, detail="Instructor has disabled offline downloads for this video.")

    return {
        "lesson_id": lesson.id,
        "video_url": lesson.video_url,
        "download_allowed": True,
        "offline_license_expires_in_seconds": 86400  # 24 hour offline playback cache
    }