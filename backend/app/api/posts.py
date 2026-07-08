# backend/app/api/posts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import List, Optional

from app.core.database import get_db
from app.core.utils import slugify
from app.schemas import PostCreate, PostUpdate, PostOut
from app.models import Post, User
from app.api.deps import get_current_user, check_admin

router = APIRouter(prefix="/posts", tags=["Posts (Blog)"])

# --- PUBLIC ROUTES ---

@router.get("", response_model=List[PostOut])
def get_posts(category: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Post).filter(Post.status == "published")
    if category:
        query = query.filter(Post.category.ilike(category))
    return query.order_by(Post.published_at.desc()).all()


@router.get("/{slug}", response_model=PostOut)
def get_post_by_slug(slug: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.slug == slug, Post.status == "published").first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay bai viet hoac bai viet chua duoc xuat ban."
        )
    return post


# --- ADMIN ROUTES ---

@router.get("/admin/all", response_model=List[PostOut])
def admin_get_all_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    return db.query(Post).order_by(Post.created_at.desc()).all()


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    slug = slugify(post_in.title)
    
    # Kiem tra trung lap slug
    dup_post = db.query(Post).filter(Post.slug == slug).first()
    if dup_post:
        # Them timestamp vao slug de tranh trung
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"
        
    published_at = datetime.now(timezone.utc) if post_in.status == "published" else None
    
    new_post = Post(
        title=post_in.title,
        slug=slug,
        summary=post_in.summary,
        content=post_in.content,
        thumbnail_url=post_in.thumbnail_url,
        category=post_in.category,
        status=post_in.status,
        author_id=current_user.id,
        published_at=published_at
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay bai viet."
        )
        
    for field, value in post_in.model_dump(exclude_unset=True).items():
        if field == "status" and value == "published" and post.status != "published":
            post.published_at = datetime.now(timezone.utc)
        setattr(post, field, value)
        
    # Cap nhat slug neu title thay doi
    if post_in.title is not None:
        new_slug = slugify(post_in.title)
        dup_post = db.query(Post).filter(Post.slug == new_slug, Post.id != post_id).first()
        if dup_post:
            new_slug = f"{new_slug}-{int(datetime.now(timezone.utc).timestamp())}"
        post.slug = new_slug
        
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay bai viet."
        )
    db.delete(post)
    db.commit()
    return None


@router.patch("/{post_id}/publish", response_model=PostOut)
def publish_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay bai viet."
        )
    post.status = "published"
    post.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return post
