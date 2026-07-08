# backend/app/api/services.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from app.core.database import get_db
from app.core.utils import slugify
from app.schemas import ServiceCreate, ServiceUpdate, ServiceOut
from app.models import Service, User
from app.api.deps import get_current_user, check_admin

router = APIRouter(prefix="/services", tags=["Services (Solutions)"])

# --- PUBLIC ROUTES ---

@router.get("", response_model=List[ServiceOut])
def get_services(db: Session = Depends(get_db)):
    return db.query(Service).filter(Service.status == "active").order_by(Service.created_at.asc()).all()


@router.get("/{slug}", response_model=ServiceOut)
def get_service_by_slug(slug: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.slug == slug, Service.status == "active").first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay dich vu hoac dich vu dang tam ngung."
        )
    return service


# --- ADMIN ROUTES ---

@router.get("/admin/all", response_model=List[ServiceOut])
def admin_get_all_services(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    return db.query(Service).order_by(Service.created_at.desc()).all()


@router.post("", response_model=ServiceOut, status_code=status.HTTP_201_CREATED)
def create_service(
    service_in: ServiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    slug = slugify(service_in.name)
    
    dup_service = db.query(Service).filter(Service.slug == slug).first()
    if dup_service:
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"
        
    new_service = Service(
        name=service_in.name,
        slug=slug,
        short_description=service_in.short_description,
        description=service_in.description,
        price=service_in.price,
        currency=service_in.currency,
        thumbnail_url=service_in.thumbnail_url,
        service_type=service_in.service_type,
        status=service_in.status
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service


@router.put("/{service_id}", response_model=ServiceOut)
def update_service(
    service_id: int,
    service_in: ServiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay dich vu."
        )
        
    for field, value in service_in.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
        
    if service_in.name is not None:
        new_slug = slugify(service_in.name)
        dup_service = db.query(Service).filter(Service.slug == new_slug, Service.id != service_id).first()
        if dup_service:
            new_slug = f"{new_slug}-{int(datetime.now(timezone.utc).timestamp())}"
        service.slug = new_slug
        
    db.commit()
    db.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_service(
    service_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay dich vu."
        )
    db.delete(service)
    db.commit()
    return None
