# backend/app/core/database.py
import psycopg2
from urllib.parse import urlparse
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# Engine ket noi PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Tu dong kiem tra ket noi con song truoc khi dung
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency de lay Session DB trong cac route API
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # 1. Check and create role / database using postgres trust connection
    db_url = settings.DATABASE_URL
    parsed = urlparse(db_url)
    db_name = parsed.path.lstrip('/')
    port = parsed.port or 5433
    host = parsed.hostname or "localhost"
    
    # Extract credentials requested
    username = parsed.username or "postgresql"
    password = parsed.password or "Thang123456"
    
    # First connect as 'postgres' (which is passwordless and exists by default on local pg_data)
    postgres_url = f"postgresql://postgres@{host}:{port}/postgres"
    
    try:
        print(f"Connecting to Postgres at {host}:{port} as user 'postgres' to setup roles...")
        conn = psycopg2.connect(postgres_url)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Create user role if not exists
        cursor.execute(f"""
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '{username}') THEN
                CREATE ROLE {username} WITH LOGIN SUPERUSER PASSWORD '{password}';
              END IF;
            END
            $$;
        """)
        print(f"User role '{username}' verified/created.")
        
        # Check and create database
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Database '{db_name}' does not exist. Creating...")
            cursor.execute(f'CREATE DATABASE "{db_name}" WITH OWNER {username} ENCODING \'UTF8\'')
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Warning: Setup via 'postgres' user trust connection failed: {e}")
        print("Will attempt direct connection with DATABASE_URL...")

    # 2. Verify connection with the final DATABASE_URL, create tables if not exists
    try:
        # Import all models so they are registered on Base
        from app.models import User, Post, Guide, Service, Order, OrderItem, Payment
        print("Creating all tables via SQLAlchemy...")
        Base.metadata.create_all(bind=engine)
        print("Database tables verified/created successfully.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        raise e

    # 3. Seed initial database data
    try:
        from app.seed import seed_db
        print("Seeding initial database data...")
        seed_db()
    except Exception as e:
        print(f"Error seeding database: {e}")
