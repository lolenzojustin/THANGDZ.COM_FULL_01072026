# backend/app/api/orders.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import random

from app.core.database import get_db
from app.schemas import OrderCreate, OrderOut, OrderStatusUpdate
from app.models import Order, OrderItem, Service, User
from app.api.deps import get_current_user, check_admin

router = APIRouter(prefix="/orders", tags=["Orders"])

def generate_order_code() -> str:
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    rand_val = random.randint(1000, 9999)
    return f"ORD-{now_str}-{rand_val}"

@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not order_in.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Don hang phai co it nhat mot dich vu."
        )
        
    order_code = generate_order_code()
    # Kiem tra tranh trung lap order_code
    while db.query(Order).filter(Order.order_code == order_code).first():
        order_code = generate_order_code()
        
    total_amount = 0.0
    db_items = []
    
    for item in order_in.items:
        service = db.query(Service).filter(Service.id == item.service_id, Service.status == "active").first()
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dich vu id {item.service_id} khong ton tai hoac da ngung hoat dong."
            )
            
        item_total = service.price * item.quantity
        total_amount += item_total
        
        db_item = OrderItem(
            service_id=service.id,
            quantity=item.quantity,
            unit_price=service.price,
            total_price=item_total
        )
        db_items.append(db_item)
        
    new_order = Order(
        user_id=current_user.id,
        order_code=order_code,
        total_amount=total_amount,
        currency="VND",
        status="pending",
        note=order_in.note
    )
    db.add(new_order)
    db.commit() # Commit de lay id cho new_order
    
    # Gan order_id cho cac item va add vao DB
    for db_item in db_items:
        db_item.order_id = new_order.id
        db.add(db_item)
        
    db.commit()
    db.refresh(new_order)
    return new_order


@router.get("/me", response_model=list[OrderOut])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Order).filter(Order.user_id == current_user.id).order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderOut)
def get_order_by_id(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay don hang."
        )
    # Chi cho phep user xem don cua hoac neu user do la admin
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ban khong co quyen xem don hang nay."
        )
    return order


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay don hang."
        )
    if order.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ban khong co quyen huy don hang nay."
        )
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Khong the huy don hang dang o trang thai {order.status}."
        )
        
    order.status = "cancelled"
    db.commit()
    db.refresh(order)
    return order


# --- ADMIN ROUTES ---

@router.get("/admin/all", response_model=list[OrderOut])
def admin_get_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    return db.query(Order).order_by(Order.created_at.desc()).all()


@router.put("/{order_id}/status", response_model=OrderOut)
def admin_update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay don hang."
        )
    order.status = status_update.status
    db.commit()
    db.refresh(order)
    return order
