from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/enrollments", tags=["Enrollments"])

@router.post("", response_model=schemas.EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    payload: schemas.EnrollmentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    course = db.query(models.Course).filter(
        models.Course.id == payload.course_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found in your workspace.")

    existing_enrollment = db.query(models.Enrollment).filter(
        models.Enrollment.user_id == current_user.id,
        models.Enrollment.course_id == payload.course_id
    ).first()

    if existing_enrollment:
        raise HTTPException(status_code=400, detail="Already enrolled in this course.")

    new_enrollment = models.Enrollment(
        user_id=current_user.id,
        course_id=payload.course_id,
        tenant_id=current_user.tenant_id
    )
    db.add(new_enrollment)
    db.commit()
    db.refresh(new_enrollment)
    return new_enrollment

@router.get("/my-courses", response_model=list[schemas.EnrollmentResponse])
def get_my_enrolled_courses(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Enrollment).filter(
        models.Enrollment.user_id == current_user.id,
        models.Enrollment.tenant_id == current_user.tenant_id
    ).all()