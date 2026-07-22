from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.dependencies import get_current_user
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/qa", tags=["Lesson Q&A"])

@router.post("/lessons/{lesson_id}/questions", response_model=schemas.QuestionResponse, status_code=status.HTTP_201_CREATED)
def ask_question(
    lesson_id: int,
    payload: schemas.QuestionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    lesson = db.query(models.Lesson).join(models.Module).join(models.Course).filter(
        models.Lesson.id == lesson_id,
        models.Course.tenant_id == current_user.tenant_id
    ).first()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found.")

    new_q = models.Question(
        content=payload.content,
        user_id=current_user.id,
        lesson_id=lesson.id,
        tenant_id=current_user.tenant_id
    )
    db.add(new_q)
    db.commit()
    db.refresh(new_q)
    return new_q

@router.post("/questions/{question_id}/answers", response_model=schemas.AnswerResponse, status_code=status.HTTP_201_CREATED)
def answer_question(
    question_id: int,
    payload: schemas.AnswerCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role not in ["admin", "teacher"]:
        raise HTTPException(status_code=403, detail="Only teachers or admins can answer student questions.")

    question = db.query(models.Question).filter(
        models.Question.id == question_id,
        models.Question.tenant_id == current_user.tenant_id
    ).first()

    if not question:
        raise HTTPException(status_code=404, detail="Question not found.")

    new_ans = models.Answer(
        content=payload.content,
        user_id=current_user.id,
        question_id=question.id
    )
    db.add(new_ans)
    db.commit()
    db.refresh(new_ans)
    return new_ans

@router.get("/lessons/{lesson_id}/questions", response_model=List[schemas.QuestionResponse])
def get_lesson_questions(
    lesson_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(models.Question).filter(
        models.Question.lesson_id == lesson_id,
        models.Question.tenant_id == current_user.tenant_id
    ).all()