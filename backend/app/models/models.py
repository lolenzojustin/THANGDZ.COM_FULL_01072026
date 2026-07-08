# backend/app/models/models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.core.database import Base

def utcnow():
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    role = Column(String, default="user")  # user, admin
    status = Column(String, default="active")  # active, inactive, banned
    email_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    posts = relationship("Post", back_populates="author")
    guides = relationship("Guide", back_populates="author")
    orders = relationship("Order", back_populates="user")
    payments = relationship("Payment", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    category = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, published, archived
    author_id = Column(Integer, ForeignKey("users.id"))
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    author = relationship("User", back_populates="posts")


class Guide(Base):
    __tablename__ = "guides"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    thumbnail_url = Column(String, nullable=True)
    level = Column(String, default="beginner")  # beginner, intermediate, advanced
    category = Column(String, nullable=True)
    status = Column(String, default="draft")  # draft, published, archived
    author_id = Column(Integer, ForeignKey("users.id"))
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    author = relationship("User", back_populates="guides")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    short_description = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    currency = Column(String, default="VND")
    thumbnail_url = Column(String, nullable=True)
    service_type = Column(String, default="service")  # service, course, digital_product, consulting
    status = Column(String, default="active")  # active, inactive, draft
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    order_items = relationship("OrderItem", back_populates="service")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    order_code = Column(String, unique=True, index=True, nullable=False)  # e.g., ORD-YYYYMMDD-XXXX
    total_amount = Column(Float, nullable=False)
    currency = Column(String, default="VND")
    status = Column(String, default="pending")  # pending, paid, cancelled, failed, refunded
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    service_id = Column(Integer, ForeignKey("services.id"))
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    # Relationships
    order = relationship("Order", back_populates="items")
    service = relationship("Service", back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id"))
    payment_method = Column(String, nullable=False)  # bank_transfer, vnpay
    provider = Column(String, nullable=True)  # manual, vnpay
    provider_transaction_id = Column(String, nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="VND")
    status = Column(String, default="pending")  # pending, success, failed, cancelled, refunded
    paid_at = Column(DateTime, nullable=True)
    raw_response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    order = relationship("Order", back_populates="payments")
    user = relationship("User", back_populates="payments")
