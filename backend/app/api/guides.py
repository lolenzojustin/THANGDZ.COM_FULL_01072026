# backend/app/api/guides.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from app.core.database import get_db
from app.core.utils import slugify
from app.schemas import GuideCreate, GuideUpdate, GuideOut
from app.models import Guide, User
from app.api.deps import get_current_user, check_admin

router = APIRouter(prefix="/guides", tags=["Guides (Tutorials)"])

# --- PUBLIC ROUTES ---

@router.get("", response_model=List[GuideOut])
def get_guides(
    level: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Guide).filter(Guide.status == "published")
    if level:
        query = query.filter(Guide.level == level)
    if category:
        query = query.filter(Guide.category.ilike(category))
    return query.order_by(Guide.published_at.desc()).all()


@router.get("/{slug}", response_model=GuideOut)
def get_guide_by_slug(slug: str, db: Session = Depends(get_db)):
    guide = db.query(Guide).filter(Guide.slug == slug, Guide.status == "published").first()
    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay huong dan hoac huong dan chua duoc xuat ban."
        )
    return guide


# --- ADMIN ROUTES ---

@router.get("/admin/all", response_model=List[GuideOut])
def admin_get_all_guides(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    return db.query(Guide).order_by(Guide.created_at.desc()).all()


@router.post("", response_model=GuideOut, status_code=status.HTTP_201_CREATED)
def create_guide(
    guide_in: GuideCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    slug = slugify(guide_in.title)
    
    dup_guide = db.query(Guide).filter(Guide.slug == slug).first()
    if dup_guide:
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"
        
    published_at = datetime.now(timezone.utc) if guide_in.status == "published" else None
    
    new_guide = Guide(
        title=guide_in.title,
        slug=slug,
        summary=guide_in.summary,
        content=guide_in.content,
        thumbnail_url=guide_in.thumbnail_url,
        level=guide_in.level,
        category=guide_in.category,
        status=guide_in.status,
        author_id=current_user.id,
        published_at=published_at
    )
    db.add(new_guide)
    db.commit()
    db.refresh(new_guide)
    return new_guide


@router.put("/{guide_id}", response_model=GuideOut)
def update_guide(
    guide_id: int,
    guide_in: GuideUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay huong dan."
        )
        
    for field, value in guide_in.model_dump(exclude_unset=True).items():
        if field == "status" and value == "published" and guide.status != "published":
            guide.published_at = datetime.now(timezone.utc)
        setattr(guide, field, value)
        
    if guide_in.title is not None:
        new_slug = slugify(guide_in.title)
        dup_guide = db.query(Guide).filter(Guide.slug == new_slug, Guide.id != guide_id).first()
        if dup_guide:
            new_slug = f"{new_slug}-{int(datetime.now(timezone.utc).timestamp())}"
        guide.slug = new_slug
        
    db.commit()
    db.refresh(guide)
    return guide


@router.delete("/{guide_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guide(
    guide_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay huong dan."
        )
    db.delete(guide)
    db.commit()
    return None


@router.patch("/{guide_id}/publish", response_model=GuideOut)
def publish_guide(
    guide_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay huong dan."
        )
    guide.status = "published"
    guide.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(guide)
    return guide
