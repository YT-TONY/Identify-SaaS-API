from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/progress", tags=["Progress & Analytics"])

@router.post("/lessons/{lesson_id}/complete", status_code=status.HTTP_200_OK)
def mark_lesson_complete(
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

    existing = db.query(models.LessonCompletion).filter(
        models.LessonCompletion.user_id == current_user.id,
        models.LessonCompletion.lesson_id == lesson_id
    ).first()

    if not existing:
        completion = models.LessonCompletion(
            user_id=current_user.id,
            lesson_id=lesson_id,
            tenant_id=current_user.tenant_id
        )
        db.add(completion)
        db.commit()

    return {"message": "Lesson marked as completed!"}

# 👨‍🏫 TEACHER VIEW: Progress of all students in a course
@router.get("/courses/{course_id}/teacher-view", response_model=List[schemas.StudentProgressOverview])
def get_teacher_course_progress(
    course_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only teachers or admins can access student progress monitoring.")

    course = db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    # Calculate total lessons in course
    total_lessons = db.query(models.Lesson).join(models.Module).filter(models.Module.course_id == course.id).count()

    # Get enrolled students
    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.course_id == course.id,
        models.Enrollment.tenant_id == current_user.tenant_id
    ).all()

    student_progress_list = []
    for enroll in enrollments:
        student = db.query(models.User).filter(models.User.id == enroll.user_id).first()
        if not student:
            continue

        completed_count = db.query(models.LessonCompletion).join(models.Lesson).join(models.Module).filter(
            models.LessonCompletion.user_id == student.id,
            models.Module.course_id == course.id
        ).count()

        percentage = (completed_count / total_lessons * 100) if total_lessons > 0 else 0.0

        student_progress_list.append(schemas.StudentProgressOverview(
            student_id=student.id,
            student_name=student.full_name,
            student_email=student.email,
            completed_lessons=completed_count,
            total_lessons=total_lessons,
            progress_percentage=round(percentage, 1)
        ))

    return student_progress_list

# 👑 ADMIN VIEW: Aggregated Workspace Completion Average
@router.get("/admin/aggregate", response_model=schemas.AdminTenantMetrics)
def get_admin_tenant_metrics(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access restricted to Tenant Administrators.")

    tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    total_students = db.query(models.User).filter(
        models.User.tenant_id == current_user.tenant_id,
        models.User.role == "student"
    ).count()

    total_courses = db.query(models.Course).filter(models.Course.tenant_id == current_user.tenant_id).count()

    # Aggregate calculation: average progress across all enrollments
    enrollments = db.query(models.Enrollment).filter(models.Enrollment.tenant_id == current_user.tenant_id).all()
    
    total_percentages = []
    for enroll in enrollments:
        total_lessons = db.query(models.Lesson).join(models.Module).filter(models.Module.course_id == enroll.course_id).count()
        if total_lessons == 0:
            continue
        
        completed_lessons = db.query(models.LessonCompletion).join(models.Lesson).join(models.Module).filter(
            models.LessonCompletion.user_id == enroll.user_id,
            models.Module.course_id == enroll.course_id
        ).count()

        total_percentages.append((completed_lessons / total_lessons) * 100)

    average_completion = (sum(total_percentages) / len(total_percentages)) if total_percentages else 0.0

    return schemas.AdminTenantMetrics(
        workspace_name=tenant.name,
        total_students=total_students,
        total_courses=total_courses,
        average_tenant_completion_rate=round(average_completion, 1)
    )