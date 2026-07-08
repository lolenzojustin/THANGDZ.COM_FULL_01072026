# backend/app/schemas/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import List, Optional, Generic, TypeVar

T = TypeVar("T")

# --- SHARED PAGINATION SCHEMA ---
class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    data: List[T]
    message: Optional[str] = None
    pagination: PaginationMeta

# --- USER SCHEMAS ---
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None

class UserOut(UserBase):
    id: int
    role: str
    status: str
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str

class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None


# --- POST SCHEMAS ---
class PostBase(BaseModel):
    title: str
    summary: Optional[str] = None
    content: str
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = "draft"

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None

class PostOut(PostBase):
    id: int
    slug: str
    author_id: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- GUIDE SCHEMAS ---
class GuideBase(BaseModel):
    title: str
    summary: Optional[str] = None
    content: str
    thumbnail_url: Optional[str] = None
    level: Optional[str] = "beginner"  # beginner, intermediate, advanced
    category: Optional[str] = None
    status: Optional[str] = "draft"

class GuideCreate(GuideBase):
    pass

class GuideUpdate(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    thumbnail_url: Optional[str] = None
    level: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None

class GuideOut(GuideBase):
    id: int
    slug: str
    author_id: int
    published_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- SERVICE SCHEMAS ---
class ServiceBase(BaseModel):
    name: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    price: float
    currency: Optional[str] = "VND"
    thumbnail_url: Optional[str] = None
    service_type: Optional[str] = "service"  # service, course, digital_product, consulting
    status: Optional[str] = "active"

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    thumbnail_url: Optional[str] = None
    service_type: Optional[str] = None
    status: Optional[str] = None

class ServiceOut(ServiceBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# --- ORDER SCHEMAS ---
class OrderItemCreate(BaseModel):
    service_id: int
    quantity: int = 1

class OrderItemOut(BaseModel):
    id: int
    service_id: int
    quantity: int
    unit_price: float
    total_price: float
    service: ServiceOut

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    note: Optional[str] = None

class OrderOut(BaseModel):
    id: int
    order_code: str
    total_amount: float
    currency: str
    status: str
    note: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str  # pending, paid, cancelled, failed, refunded


# --- PAYMENT SCHEMAS ---
class PaymentCreate(BaseModel):
    order_id: int
    payment_method: str  # bank_transfer, vnpay

class PaymentOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    payment_method: str
    provider: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PaymentConfirm(BaseModel):
    status: str  # success, failed
    provider_transaction_id: Optional[str] = None
