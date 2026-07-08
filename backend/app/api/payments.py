# backend/app/api/payments.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from typing import Optional

from app.core.database import get_db
from app.schemas import PaymentCreate, PaymentOut, PaymentConfirm
from app.models import Payment, Order, User
from app.api.deps import get_current_user, check_admin

router = APIRouter(prefix="/payments", tags=["Payments"])

# Thong tin tai khoan ngan hang nhan thanh toan ( VietQR )
BANK_ID = "MB"  # Ngan hang Quan doi
ACCOUNT_NO = "123456789999"
ACCOUNT_NAME = "LE MINH THANG"

@router.post("/create", response_model=dict)
def create_payment_session(
    payment_in: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Kiem tra don hang
    order = db.query(Order).filter(Order.id == payment_in.order_id).first()
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay don hang."
        )
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Don hang khong thuoc ve tai khoan cua ban."
        )
    if order.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Don hang khong o trang thai thanh toan (Trang thai hien tai: {order.status})."
        )
        
    # Tao thanh toan moi hoac tai su dung thanh toan cu dang pending
    payment = db.query(Payment).filter(
        Payment.order_id == order.id, 
        Payment.status == "pending"
    ).first()
    
    if not payment:
        payment = Payment(
            order_id=order.id,
            user_id=current_user.id,
            payment_method=payment_in.payment_method,
            provider="manual",
            amount=order.total_amount,
            currency=order.currency,
            status="pending"
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)
        
    # Tao link QR code dong bang VietQR
    # Url encode account name
    import urllib.parse
    encoded_name = urllib.parse.quote(ACCOUNT_NAME)
    qr_url = f"https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact.png?amount={int(order.total_amount)}&addInfo={order.order_code}&accountName={encoded_name}"
    
    return {
        "payment_id": payment.id,
        "order_id": order.id,
        "order_code": order.order_code,
        "amount": order.total_amount,
        "payment_method": payment.payment_method,
        "bank_name": "Ngan hang TMCP Quan doi (MBBank)",
        "account_no": ACCOUNT_NO,
        "account_name": ACCOUNT_NAME,
        "memo": order.order_code,
        "qr_url": qr_url,
        "status": payment.status
    }


@router.get("/my-transactions", response_model=list[PaymentOut])
def get_my_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Payment).filter(Payment.user_id == current_user.id).order_by(Payment.created_at.desc()).all()


# --- ADMIN ROUTES ---

@router.get("/admin/all", response_model=list[PaymentOut])
def admin_get_all_payments(
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    return db.query(Payment).order_by(Payment.created_at.desc()).all()


@router.post("/admin/{payment_id}/confirm", response_model=PaymentOut)
def admin_confirm_payment(
    payment_id: int,
    confirm_in: PaymentConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_admin)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Khong tim thay giao dich thanh toan."
        )
        
    if payment.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Giao dich da duoc xu ly truoc do."
        )
        
    payment.status = "success" if confirm_in.status == "success" else "failed"
    payment.paid_at = datetime.now(timezone.utc) if confirm_in.status == "success" else None
    payment.provider_transaction_id = confirm_in.provider_transaction_id
    
    # Cap nhat trang thai don hang tuong ung
    order = db.query(Order).filter(Order.id == payment.order_id).first()
    if order:
        if confirm_in.status == "success":
            order.status = "paid"
        else:
            order.status = "failed"
            
    db.commit()
    db.refresh(payment)
    return payment
