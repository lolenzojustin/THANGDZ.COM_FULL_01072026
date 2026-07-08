# backend/app/seed.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models import User, Post, Guide, Service

def seed_db():
    db: Session = SessionLocal()
    
    # 1. Seed Admin User
    admin_email = "admin@personal.com"
    admin = db.query(User).filter(User.email == admin_email).first()
    if not admin:
        print("Creating admin user...")
        admin = User(
            email=admin_email,
            full_name="Le Minh Thang",
            phone="0987654321",
            password_hash=get_password_hash("admin123"),
            role="admin",
            status="active"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
    else:
        print("Admin user already exists.")
        
    # 2. Seed Services
    if db.query(Service).count() == 0:
        print("Seeding services...")
        services_data = [
            {
                "name": "Thiet Ke Website Ca Nhan Chuyen Nghiep",
                "slug": "thiet-ke-website-ca-nhan-chuyen-nghiep",
                "short_description": "Xay dung thuong hieu ca nhan voi landing page hoac blog hien dai, responsive, chuan SEO.",
                "description": "Dich vu thiet ke website ca nhan tron goi. Bao gom: giao dien bat mat, toc do tai trang nhanh duoi 1s, tich hop he thong blog, CMS quan ly tin tuc va ket noi cac cong thanh toan co ban. Bao hanh ho tro 12 thang.",
                "price": 5000000.0,
                "service_type": "service",
                "status": "active"
            },
            {
                "name": "Cho Thue Tool Tao Video AI",
                "slug": "cho-thue-tool-tao-video-ai",
                "short_description": "Cho thue tool tao video AI tu kich ban, hinh anh va giong doc phu hop lam noi dung marketing.",
                "description": "Dich vu cho thue tool tao video AI giup tao video ngan, video quang cao, video noi dung mang xa hoi va video gioi thieu san pham tu prompt, kich ban, hinh anh hoac giong doc. Phu hop cho ca nhan, creator va doanh nghiep can san xuat noi dung nhanh.",
                "price": 1200000.0,
                "service_type": "digital_product",
                "status": "active"
            },
            {
                "name": "Lam Chatbot AI Theo Yeu Cau",
                "slug": "lam-chatbot-ai-theo-yeu-cau",
                "short_description": "Thiet ke chatbot AI tu dong tu van, cham soc khach hang va tra loi theo du lieu rieng cua ban.",
                "description": "Dich vu xay dung chatbot AI theo yeu cau cho website, fanpage hoac quy trinh noi bo. Chatbot co the tu van san pham, tra loi cau hoi thuong gap, thu thap thong tin khach hang va ket noi API/database tuy nhu cau.",
                "price": 800000.0,
                "service_type": "service",
                "status": "active"
            }
        ]
        for s in services_data:
            db.add(Service(**s))
        db.commit()
    else:
        print("Services already seeded.")
        
    # 3. Seed Posts (News)
    if db.query(Post).count() == 0:
        print("Seeding blog posts...")
        posts_data = [
            {
                "title": "Xu huong xay dung thuong hieu ca nhan nam 2026",
                "slug": "xu-huong-xay-dung-thuong-hieu-ca-nhan-nam-2026",
                "summary": "Tai sao moi lap trinh vien hay designer deu can mot website ca nhan rieng de nang cao gia tri va co them khach hang.",
                "content": "Trong ky nguyen so, resume giay da tro nen loi thoi. Mot website ca nhan mang ten mien rieng chinh la tam danh thiep uy tin nhat giup ban noi bat truoc cac nha tuyen dung va khach hang. Bai viet nay phan tich cac yeu to quyet dinh su thanh cong cua mot web ca nhan: thiet ke tối giản, khoi choi du an va blog chia se kien thuc thuc te.",
                "category": "Tech News",
                "status": "published",
                "author_id": admin.id,
                "published_at": datetime.utcnow()
            },
            {
                "title": "Tai sao ban nen trien khai du an khong dung Docker?",
                "slug": "tai-sao-ban-nen-trien-khai-du-an-khong-dung-docker",
                "summary": "Phan tich uu nhuoc diem cua viec chay truc tiep services tren VPS so voi su dung Docker container.",
                "content": "Docker rat tot cho moi truong lon va microservices. Tuy nhien voi cac du an MVP, blog hoac web ca nhan, Docker lai gay ra overhead ve tai nguyen (RAM/CPU), tang do phuc tap cua he thong va tao ra rao can lon trong viec monitoring logs. Chay truc tiep bang systemd hoac PM2 giup tan dung 100% hieu nang VPS va de dang cau hinh cac port tiep can truc tiep.",
                "category": "DevOps",
                "status": "published",
                "author_id": admin.id,
                "published_at": datetime.utcnow()
            }
        ]
        for p in posts_data:
            db.add(Post(**p))
        db.commit()
    else:
        print("Blog posts already seeded.")
        
    # 4. Seed Guides (Tutorials)
    if db.query(Guide).count() == 0:
        print("Seeding guides...")
        guides_data = [
            {
                "title": "Huong dan thiet lap PostgreSQL local chay tren port 5433",
                "slug": "huong-dan-thiet-lap-postgresql-local-chay-tren-port-5433",
                "summary": "Tung buoc chi tiet cach khoi tao va chay PostgreSQL doc lap ma khong gay anh huong den service he thong.",
                "level": "beginner",
                "category": "PostgreSQL",
                "status": "published",
                "author_id": admin.id,
                "published_at": datetime.utcnow(),
                "content": "Buoc 1: Chay lenh `initdb -D pg_data --auth=trust` de tao cluster.\nBuoc 2: Chay postgres daemon bang `postgres -D pg_data -p 5433`.\nBuoc 3: Kiem tra cong ket noi bang `pg_isready -p 5433`.\nDay la phuong phap giup ban duy tri moi truong co so du lieu co lap tuyet doi o may local ma khong can bat Docker."
            },
            {
                "title": "Xay dung luong thanh toan VietQR dong voi FastAPI va Next.js",
                "slug": "xay-dung-luong-thanh-toan-vietqr-dong-voi-fastapi-va-next-js",
                "summary": "Huong dan sinh ma QR thanh toan ngan hang tu dong di kem so tien va ma hoa don.",
                "level": "intermediate",
                "category": "Backend",
                "status": "published",
                "author_id": admin.id,
                "published_at": datetime.utcnow(),
                "content": "VietQR cung cap API dinh dang hinh anh rat thuan tien de tao ma QR quet nhanh. Cong thuc tao link anh:\n`https://img.vietqr.io/image/{BANK_ID}-{ACCOUNT_NO}-compact.png?amount={AMOUNT}&addInfo={ORDER_CODE}&accountName={ACCOUNT_NAME}`.\nKhi nguoi dung quet ma nay bang app ngan hang, thong tin so tien va loi nhan se tu dong dien san giup han che toi da sai sot khi nhap tay."
            }
        ]
        for g in guides_data:
            db.add(Guide(**g))
        db.commit()
    else:
        print("Guides already seeded.")

    print("Database seeding completed successfully!")
    db.close()

if __name__ == "__main__":
    seed_db()
