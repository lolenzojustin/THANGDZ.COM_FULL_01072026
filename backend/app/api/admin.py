# backend/app/api/admin.py
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime, timezone
from pathlib import Path
import shutil
import uuid

from app.core.database import get_db
from app.core.utils import slugify
from app.schemas import (
    UserOut,
    PostCreate, PostUpdate, PostOut,
    GuideCreate, GuideUpdate, GuideOut,
    ServiceCreate, ServiceUpdate, ServiceOut,
)
from app.models import User, Post, Guide, Service, Order, Payment, OrderItem
from app.api.deps import check_admin

router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "image/avif"}

# --- HELPERS ---

def paginate(query, page: int, limit: int):
    total = query.count()
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    total_pages = (total + limit - 1) // limit
    return {
        "success": True,
        "data": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
        },
    }


def ok_response(data: Any, message: str = None):
    resp = {"success": True, "data": data}
    if message:
        resp["message"] = message
    return resp


@router.post("/media/upload")
def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(check_admin),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chi ho tro upload anh jpg, png, webp, gif hoac avif.",
        )

    original_suffix = Path(file.filename or "").suffix.lower()
    suffix = original_suffix if original_suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"} else ".jpg"
    filename = f"{uuid.uuid4().hex}{suffix}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / filename

    with target.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return ok_response({
        "filename": filename,
        "url": f"http://localhost:8000/uploads/{filename}",
    }, "Upload thanh cong.")


# --- Pydantic schemas for request bodies ---

class UserStatusUpdate(BaseModel):
    user_status: str  # active, inactive, banned

class UserRoleUpdate(BaseModel):
    role: str  # user, admin

class OrderStatusUpdate(BaseModel):
    status: str
    admin_note: Optional[str] = None

class PaymentRefund(BaseModel):
    reason: Optional[str] = None


# --- DASHBOARD ---

@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    total_users = db.query(User).count()
    total_posts = db.query(Post).filter(Post.status == "published").count()
    total_guides = db.query(Guide).filter(Guide.status == "published").count()
    total_services = db.query(Service).count()
    total_orders = db.query(Order).count()

    revenue_query = db.query(func.sum(Order.total_amount)).filter(Order.status == "paid").scalar()
    total_revenue = float(revenue_query) if revenue_query else 0.0

    pending_payments_count = db.query(Payment).filter(Payment.status == "pending").count()

    recent_orders_db = (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )
    recent_orders = []
    for order in recent_orders_db:
        user_email = db.query(User.email).filter(User.id == order.user_id).scalar()
        recent_orders.append({
            "id": order.id,
            "order_code": order.order_code,
            "total_amount": order.total_amount,
            "status": order.status,
            "user_email": user_email or "Unknown",
            "created_at": order.created_at,
        })

    recent_payments_db = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .limit(5)
        .all()
    )
    recent_payments = []
    for p in recent_payments_db:
        user_email = db.query(User.email).filter(User.id == p.user_id).scalar()
        recent_payments.append({
            "id": p.id,
            "order_id": p.order_id,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "status": p.status,
            "user_email": user_email or "Unknown",
            "created_at": p.created_at,
        })

    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "total_posts": total_posts,
            "total_guides": total_guides,
            "total_services": total_services,
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "pending_payments_count": pending_payments_count,
            "recent_orders": recent_orders,
            "recent_payments": recent_payments,
        },
    }


@router.get("/dashboard/revenue-chart")
def get_revenue_chart(
    days: int = Query(default=30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    from datetime import datetime, timezone, timedelta

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    results = (
        db.query(
            func.date(Order.created_at).label("date"),
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .filter(Order.status == "paid", Order.created_at >= start_date)
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
        .all()
    )

    data = [
        {
            "date": str(r.date),
            "revenue": float(r.revenue or 0),
            "order_count": r.order_count,
        }
        for r in results
    ]
    return ok_response(data)


# --- USERS ---

@router.get("/users")
def get_users(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    query = db.query(User)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (User.email.ilike(search_term)) | (User.full_name.ilike(search_term))
        )
    if status:
        query = query.filter(User.status == status)
    if role:
        query = query.filter(User.role == role)

    query = query.order_by(User.created_at.desc())
    return paginate(query, page, limit)


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay nguoi dung.")

    orders_count = db.query(Order).filter(Order.user_id == user_id).count()
    payments_count = db.query(Payment).filter(Payment.user_id == user_id).count()

    return ok_response({
        **UserOut.model_validate(user).model_dump(),
        "orders_count": orders_count,
        "payments_count": payments_count,
    })


@router.patch("/users/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    body: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    if body.user_status not in ["active", "inactive", "banned"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Trang thai khong hop le.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay nguoi dung.",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ban khong the tu khoa tai khoan cua chinh minh.",
        )

    user.status = body.user_status
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    body: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    if body.role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vai tro khong hop le.",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay nguoi dung.",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ban khong the tu ha cap quyen admin cua chinh minh.",
        )

    user.role = body.role
    db.commit()
    db.refresh(user)
    return user


# --- BACKWARD COMPAT: old non-paginated endpoints (deprecated, use /admin/users instead) ---

@router.get("/users-all", response_model=List[UserOut], include_in_schema=False)
def get_all_users_deprecated(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    return db.query(User).order_by(User.created_at.desc()).all()


# ===================== POSTS =====================

@router.get("/posts")
def list_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    query = db.query(Post)
    if search:
        s = f"%{search}%"
        query = query.filter(Post.title.ilike(s) | Post.summary.ilike(s))
    if status:
        query = query.filter(Post.status == status)
    if category:
        query = query.filter(Post.category.ilike(f"%{category}%"))
    query = query.order_by(Post.created_at.desc())
    return paginate(query, page, limit)


@router.get("/posts/{post_id}", response_model=PostOut)
def get_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet.")
    return post


@router.post("/posts", response_model=PostOut, status_code=201)
def create_post(post_in: PostCreate, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    slug = slugify(post_in.title)
    dup = db.query(Post).filter(Post.slug == slug).first()
    if dup:
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"

    published_at = datetime.now(timezone.utc) if post_in.status == "published" else None
    new_post = Post(
        title=post_in.title, slug=slug, summary=post_in.summary,
        content=post_in.content, thumbnail_url=post_in.thumbnail_url,
        category=post_in.category, status=post_in.status,
        author_id=current_user.id, published_at=published_at,
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return new_post


@router.put("/posts/{post_id}", response_model=PostOut)
def update_post(post_id: int, post_in: PostUpdate, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet.")

    for field, value in post_in.model_dump(exclude_unset=True).items():
        if field == "status" and value == "published" and post.status != "published":
            post.published_at = datetime.now(timezone.utc)
        setattr(post, field, value)

    if post_in.title is not None:
        new_slug = slugify(post_in.title)
        dup = db.query(Post).filter(Post.slug == new_slug, Post.id != post_id).first()
        if dup:
            new_slug = f"{new_slug}-{int(datetime.now(timezone.utc).timestamp())}"
        post.slug = new_slug

    db.commit()
    db.refresh(post)
    return post


@router.delete("/posts/{post_id}", status_code=204)
def delete_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet.")
    db.delete(post)
    db.commit()
    return None


@router.patch("/posts/{post_id}/publish", response_model=PostOut)
def publish_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet.")
    post.status = "published"
    post.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(post)
    return post


@router.patch("/posts/{post_id}/archive", response_model=PostOut)
def archive_post(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Khong tim thay bai viet.")
    post.status = "archived"
    db.commit()
    db.refresh(post)
    return post


# ===================== GUIDES =====================

@router.get("/guides")
def list_guides(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    level: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    query = db.query(Guide)
    if search:
        s = f"%{search}%"
        query = query.filter(Guide.title.ilike(s) | Guide.summary.ilike(s))
    if status:
        query = query.filter(Guide.status == status)
    if level:
        query = query.filter(Guide.level == level)
    if category:
        query = query.filter(Guide.category.ilike(f"%{category}%"))
    query = query.order_by(Guide.created_at.desc())
    return paginate(query, page, limit)


@router.get("/guides/{guide_id}", response_model=GuideOut)
def get_guide(guide_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Khong tim thay huong dan.")
    return guide


@router.post("/guides", response_model=GuideOut, status_code=201)
def create_guide(guide_in: GuideCreate, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    slug = slugify(guide_in.title)
    dup = db.query(Guide).filter(Guide.slug == slug).first()
    if dup:
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"

    published_at = datetime.now(timezone.utc) if guide_in.status == "published" else None
    new_guide = Guide(
        title=guide_in.title, slug=slug, summary=guide_in.summary,
        content=guide_in.content, thumbnail_url=guide_in.thumbnail_url,
        level=guide_in.level, category=guide_in.category, status=guide_in.status,
        author_id=current_user.id, published_at=published_at,
    )
    db.add(new_guide)
    db.commit()
    db.refresh(new_guide)
    return new_guide


@router.put("/guides/{guide_id}", response_model=GuideOut)
def update_guide(guide_id: int, guide_in: GuideUpdate, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Khong tim thay huong dan.")

    for field, value in guide_in.model_dump(exclude_unset=True).items():
        if field == "status" and value == "published" and guide.status != "published":
            guide.published_at = datetime.now(timezone.utc)
        setattr(guide, field, value)

    if guide_in.title is not None:
        new_slug = slugify(guide_in.title)
        dup = db.query(Guide).filter(Guide.slug == new_slug, Guide.id != guide_id).first()
        if dup:
            new_slug = f"{new_slug}-{int(datetime.now(timezone.utc).timestamp())}"
        guide.slug = new_slug

    db.commit()
    db.refresh(guide)
    return guide


@router.delete("/guides/{guide_id}", status_code=204)
def delete_guide(guide_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Khong tim thay huong dan.")
    db.delete(guide)
    db.commit()
    return None


@router.patch("/guides/{guide_id}/publish", response_model=GuideOut)
def publish_guide(guide_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Khong tim thay huong dan.")
    guide.status = "published"
    guide.published_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(guide)
    return guide


@router.patch("/guides/{guide_id}/archive", response_model=GuideOut)
def archive_guide(guide_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    guide = db.query(Guide).filter(Guide.id == guide_id).first()
    if not guide:
        raise HTTPException(status_code=404, detail="Khong tim thay huong dan.")
    guide.status = "archived"
    db.commit()
    db.refresh(guide)
    return guide


# ===================== SERVICES =====================

@router.get("/services")
def list_services(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    service_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    query = db.query(Service)
    if search:
        s = f"%{search}%"
        query = query.filter(Service.name.ilike(s) | Service.short_description.ilike(s))
    if status:
        query = query.filter(Service.status == status)
    if service_type:
        query = query.filter(Service.service_type == service_type)
    query = query.order_by(Service.created_at.desc())
    return paginate(query, page, limit)


@router.get("/services/{service_id}", response_model=ServiceOut)
def get_service(service_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Khong tim thay dich vu.")
    return service


@router.post("/services", response_model=ServiceOut, status_code=201)
def create_service(service_in: ServiceCreate, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    slug = slugify(service_in.name)
    dup = db.query(Service).filter(Service.slug == slug).first()
    if dup:
        slug = f"{slug}-{int(datetime.now(timezone.utc).timestamp())}"

    new_service = Service(
        name=service_in.name, slug=slug,
        short_description=service_in.short_description,
        description=service_in.description,
        price=service_in.price, currency=service_in.currency,
        thumbnail_url=service_in.thumbnail_url,
        service_type=service_in.service_type, status=service_in.status,
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service


@router.put("/services/{service_id}", response_model=ServiceOut)
def update_service(service_id: int, service_in: ServiceUpdate, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Khong tim thay dich vu.")

    for field, value in service_in.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    if service_in.name is not None:
        new_slug = slugify(service_in.name)
        dup = db.query(Service).filter(Service.slug == new_slug, Service.id != service_id).first()
        if dup:
            new_slug = f"{new_slug}-{int(datetime.now(timezone.utc).timestamp())}"
        service.slug = new_slug

    db.commit()
    db.refresh(service)
    return service


@router.delete("/services/{service_id}", status_code=204)
def delete_service(service_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Khong tim thay dich vu.")
    db.delete(service)
    db.commit()
    return None


# ===================== ORDERS =====================

@router.get("/orders")
def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    query = db.query(Order)
    if search:
        s = f"%{search}%"
        query = query.filter(Order.order_code.ilike(s))
    if status:
        query = query.filter(Order.status == status)
    if date_from:
        query = query.filter(Order.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        query = query.filter(Order.created_at <= datetime.fromisoformat(date_to))

    total = query.count()
    offset = (page - 1) * limit
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()
    total_pages = (total + limit - 1) // limit

    items = []
    for o in orders:
        user_email = db.query(User.email).filter(User.id == o.user_id).scalar()
        items.append({
            "id": o.id, "order_code": o.order_code,
            "total_amount": o.total_amount, "currency": o.currency,
            "status": o.status, "note": o.note,
            "user_email": user_email or "Unknown",
            "created_at": o.created_at, "updated_at": o.updated_at,
        })

    return {
        "success": True,
        "data": items,
        "pagination": {
            "page": page, "limit": limit, "total": total, "total_pages": total_pages,
        },
    }


@router.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Khong tim thay don hang.")

    user = db.query(User).filter(User.id == order.user_id).first()
    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()

    order_items = []
    for item in items:
        svc = db.query(Service).filter(Service.id == item.service_id).first()
        order_items.append({
            "id": item.id, "service_id": item.service_id,
            "quantity": item.quantity, "unit_price": item.unit_price,
            "total_price": item.total_price,
            "service_name": svc.name if svc else "Unknown",
        })

    payments = db.query(Payment).filter(Payment.order_id == order_id).all()
    payment_list = [
        {
            "id": p.id, "payment_method": p.payment_method,
            "amount": p.amount, "status": p.status,
            "provider_transaction_id": p.provider_transaction_id,
            "paid_at": p.paid_at, "created_at": p.created_at,
        }
        for p in payments
    ]

    return ok_response({
        "id": order.id, "order_code": order.order_code,
        "total_amount": order.total_amount, "currency": order.currency,
        "status": order.status, "note": order.note,
        "created_at": order.created_at, "updated_at": order.updated_at,
        "user": {
            "id": user.id if user else None,
            "email": user.email if user else "Unknown",
            "full_name": user.full_name if user else None,
        } if user else None,
        "items": order_items,
        "payments": payment_list,
    })


@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Khong tim thay don hang.")

    new_status = body.get("status")
    if new_status not in ["pending", "paid", "cancelled", "failed", "refunded"]:
        raise HTTPException(status_code=400, detail="Trang thai khong hop le.")

    order.status = new_status
    if body.get("admin_note"):
        order.note = (order.note or "") + f"\n[Admin {current_user.email}]: {body['admin_note']}"

    db.commit()
    db.refresh(order)
    return ok_response(order)


# ===================== PAYMENTS =====================

@router.get("/payments")
def list_payments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    payment_method: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    query = db.query(Payment)
    if status:
        query = query.filter(Payment.status == status)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)

    total = query.count()
    offset = (page - 1) * limit
    payments = query.order_by(Payment.created_at.desc()).offset(offset).limit(limit).all()
    total_pages = (total + limit - 1) // limit

    items = []
    for p in payments:
        user_email = db.query(User.email).filter(User.id == p.user_id).scalar()
        order_code = db.query(Order.order_code).filter(Order.id == p.order_id).scalar()
        items.append({
            "id": p.id, "order_id": p.order_id, "order_code": order_code or "Unknown",
            "user_email": user_email or "Unknown",
            "payment_method": p.payment_method, "provider": p.provider,
            "amount": p.amount, "currency": p.currency,
            "status": p.status, "provider_transaction_id": p.provider_transaction_id,
            "paid_at": p.paid_at, "created_at": p.created_at,
        })

    return {
        "success": True,
        "data": items,
        "pagination": {
            "page": page, "limit": limit, "total": total, "total_pages": total_pages,
        },
    }


@router.get("/payments/{payment_id}")
def get_payment(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(check_admin)):
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Khong tim thay giao dich.")
    return ok_response(p)


@router.post("/payments/{payment_id}/confirm")
def confirm_payment(
    payment_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Khong tim thay giao dich thanh toan.")
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail="Giao dich da duoc xu ly truoc do.")

    confirm_status = body.get("status", "success")
    tx_id = body.get("provider_transaction_id")

    payment.status = "success" if confirm_status == "success" else "failed"
    payment.paid_at = datetime.now(timezone.utc) if confirm_status == "success" else None
    payment.provider_transaction_id = tx_id

    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
        order.status = "paid" if confirm_status == "success" else "failed"

    db.commit()
    db.refresh(payment)
    return ok_response(payment, "Xac nhan thanh toan thanh cong.")


@router.post("/payments/{payment_id}/refund")
def refund_payment(
    payment_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin),
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Khong tim thay giao dich.")
    if payment.status != "success":
        raise HTTPException(status_code=400, detail="Chi co the refund giao dich da thanh toan.")

    payment.status = "refunded"
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
        order.status = "refunded"

    db.commit()
    db.refresh(payment)
    return ok_response(payment, "Hoan tien thanh cong.")
