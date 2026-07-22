from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import require_super_admin
import app.models as models

router = APIRouter(prefix="/api/v1/super-admin", tags=["Super Admin Platform Layer"])

# List all tenants across the SaaS
@router.get("/tenants")
def list_all_tenants(
    admin: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    return db.query(models.Tenant).all()

# Toggle workspace active state (Suspend / Reinstate Tenant)
@router.patch("/tenants/{tenant_id}/toggle-status")
def toggle_tenant_status(
    tenant_id: int,
    admin: models.User = Depends(require_super_admin),
    db: Session = Depends(get_db)
):
    tenant = db.query(models.Tenant).filter(models.Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")

    tenant.is_active = not tenant.is_active
    db.commit()

    status_str = "activated" if tenant.is_active else "suspended"
    return {"message": f"Workspace '{tenant.name}' has been {status_str}."}