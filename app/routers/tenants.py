from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
import app.models as models
import app.schemas as schemas

router = APIRouter(prefix="/api/v1/tenants", tags=["Tenant Management"])

@router.patch("/settings", response_model=schemas.TenantResponse)
def update_tenant_settings(
    payload: schemas.TenantSettingsUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Only Tenant Admins can change workspace features/branding
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admins can update settings.")

    tenant = db.query(models.Tenant).filter(models.Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant workspace not found.")

    if payload.name:
        tenant.name = payload.name
    if payload.primary_color:
        tenant.primary_color = payload.primary_color
    if payload.secondary_color:
        tenant.secondary_color = payload.secondary_color
    if payload.features:
        tenant.features = payload.features.dict()

    db.commit()
    db.refresh(tenant)
    return tenant