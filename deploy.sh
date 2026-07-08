#!/bin/bash

# ==============================================================================
# SCRIPT TỰ ĐỘNG TRIỂN KHAI DỰ ÁN THANGDZ.COM (BACKEND + FRONTENDS) LÊN VPS UBUNTU
# ==============================================================================

# >>> CẤU HÌNH TÊN MIỀN VÀ EMAIL CỦA BẠN TẠI ĐÂY <<<
DOMAIN="thangdz.com"
EMAIL="leminhthang7896@gmail.com"
# =================================================

# Thiết lập màu sắc hiển thị
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================================${NC}"
echo -e "${BLUE}          TỰ ĐỘNG TRIỂN KHAI DỰ ÁN THANGDZ.COM TRÊN UBUNTU 22.04      ${NC}"
echo -e "${BLUE}======================================================================${NC}"

# 1. Kiểm tra quyền root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}Lỗi: Vui lòng chạy script này với quyền root (Sử dụng: sudo ./deploy.sh)${NC}"
  exit 1
fi

# Xác định user thật đã gọi sudo để chạy PM2 dưới user đó (tránh chạy PM2 bằng root)
REAL_USER=$SUDO_USER
if [ -z "$REAL_USER" ] || [ "$REAL_USER" = "root" ]; then
  # Nếu chạy trực tiếp bằng root, cố gắng lấy user thường đầu tiên có thư mục /home
  REAL_USER=$(awk -F: '$3>=1000 && $3<60000 {print $1}' /etc/passwd | head -n 1)
  if [ -z "$REAL_USER" ]; then
    REAL_USER="root"
  fi
fi

# Lấy đường dẫn thư mục hiện tại của dự án
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo -e "${GREEN}Thư mục dự án:${NC} $PROJECT_DIR"
echo -e "${GREEN}Chạy các dịch vụ Node/PM2 dưới user:${NC} $REAL_USER"

# Phân quyền sở hữu toàn bộ thư mục dự án cho REAL_USER để tránh lỗi ghi file/tạo thư mục (ví dụ npm install)
if [ "$REAL_USER" != "root" ]; then
  echo -e "Đang phân quyền sở hữu thư mục dự án cho user ${GREEN}$REAL_USER${NC}..."
  chown -R $REAL_USER:$REAL_USER "$PROJECT_DIR"
fi

# 2. Cấu hình tên miền và email cấu hình SSL (Đã được định nghĩa ở đầu file)
echo -e "\n${YELLOW}--- THÔNG TIN TÊN MIỀN & SSL ---${NC}"
echo -e "Tên miền cấu hình hiện tại: ${GREEN}$DOMAIN${NC}"
echo -e "Email đăng ký SSL hiện tại: ${GREEN}$EMAIL${NC}"
echo -e "\nBạn có muốn thay đổi thông tin này không?"
read -p "Nhập tên miền mới (Nhấn Enter để giữ nguyên '$DOMAIN'): " INPUT_DOMAIN
if [ -n "$INPUT_DOMAIN" ]; then
  DOMAIN="$INPUT_DOMAIN"
fi

read -p "Nhập email mới (Nhấn Enter để giữ nguyên '$EMAIL'): " INPUT_EMAIL
if [ -n "$INPUT_EMAIL" ]; then
  EMAIL="$INPUT_EMAIL"
fi

echo -e "\n${GREEN}Cấu hình dịch vụ sẽ là:${NC}"
echo -e " - Website chính:  ${BLUE}https://$DOMAIN${NC} và ${BLUE}https://www.$DOMAIN${NC} (Port 3000)"
echo -e " - Trang Quản trị:  ${BLUE}https://$DOMAIN/admin${NC} (Port 3001)"
echo -e " - Backend API:    ${BLUE}https://$DOMAIN/api${NC} (Port 8000)"
echo -e " - Email SSL:       ${BLUE}$EMAIL${NC}"

# Lấy IP public của VPS và kiểm tra cấu hình DNS
echo -e "\n${YELLOW}--- KIỂM TRA ĐỊA CHỈ IP PUBLIC VÀ DNS ---${NC}"
echo -e "Đang kiểm tra địa chỉ IP public của VPS..."
VPS_IP=$(curl -s --max-time 5 https://api.ipify.org || curl -s --max-time 5 https://ifconfig.me)

if [ -n "$VPS_IP" ]; then
  echo -e "Địa chỉ IP public của VPS này là: ${GREEN}$VPS_IP${NC}"
else
  echo -e "${YELLOW}Cảnh báo: Không thể tự động xác định IP public của VPS. Sẽ bỏ qua so sánh địa chỉ IP.${NC}"
fi

check_dns() {
  local domain=$1
  local expected_ip=$2
  
  echo -n " - Đang kiểm tra DNS cho $domain... "
  
  # Giải quyết IP của tên miền bằng getent
  local resolved_ip=$(getent ahosts "$domain" | head -n 1 | awk '{print $1}')
  
  if [ -z "$resolved_ip" ]; then
    echo -e "${RED}LỖI (Không thể phân giải tên miền)${NC}"
    return 1
  fi
  
  if [ -n "$expected_ip" ] && [ "$resolved_ip" != "$expected_ip" ]; then
    echo -e "${YELLOW}CẢNH BÁO (Trỏ về IP $resolved_ip, khác với IP VPS $expected_ip)${NC}"
    return 2
  fi
  
  echo -e "${GREEN}OK (Trỏ đúng về $resolved_ip)${NC}"
  return 0
}

DNS_ERRORS=0
check_dns "$DOMAIN" "$VPS_IP" || DNS_ERRORS=$((DNS_ERRORS + 1))
check_dns "www.$DOMAIN" "$VPS_IP" || DNS_ERRORS=$((DNS_ERRORS + 1))

if [ $DNS_ERRORS -gt 0 ]; then
  echo -e "\n${RED}Cảnh báo: Phát hiện bản ghi DNS chưa trỏ đúng về VPS này hoặc chưa có hiệu lực.${NC}"
  echo -e "${YELLOW}Nếu tiếp tục, việc cài đặt SSL (Certbot) cho tên miền lỗi sẽ thất bại.${NC}"
  read -p "Bạn có muốn tiếp tục chạy cài đặt không? (y/n, mặc định y): " CONTINUE_INSTALL
  if [[ "$CONTINUE_INSTALL" =~ ^[nN]$ ]]; then
    echo -e "${RED}Đã hủy quá trình cài đặt. Vui lòng cấu hình DNS và chạy lại script.${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}Chúc mừng! Các bản ghi DNS đã trỏ đúng về VPS này.${NC}"
fi

echo -e "\n${YELLOW}Lưu ý: Hãy chắc chắn rằng bạn đã trỏ các bản ghi A/CNAME của tên miền chính (@ và www) về IP VPS.${NC}"
read -p "Nhấn [Enter] để bắt đầu cài đặt..."

# 3. Tạo Swap 2GB nếu RAM của VPS quá thấp (< 3GB) để tránh lỗi Out of Memory khi Build Next.js
echo -e "\n${YELLOW}--- KIỂM TRA & CẤU HÌNH SWAP MEMORY ---${NC}"
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
TOTAL_SWAP=$(free -m | awk '/^Swap:/{print $2}')
COMBINED=$((TOTAL_RAM + TOTAL_SWAP))

if [ $COMBINED -lt 3000 ]; then
  if [ ! -f /swapfile ]; then
    echo -e "${YELLOW}Phát hiện RAM thấp ($TOTAL_RAM MB). Đang tạo swap 2GB để hỗ trợ quá trình build Next.js...${NC}"
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo -e "${GREEN}Đã tạo swap thành công!${NC}"
  else
    echo -e "${GREEN}Đã tồn tại swapfile trên hệ thống.${NC}"
  fi
else
  echo -e "${GREEN}Hệ thống có đủ bộ nhớ RAM ($TOTAL_RAM MB). Bỏ qua tạo swap.${NC}"
fi

# 4. Cập nhật hệ thống và cài đặt Dependencies cơ bản
echo -e "\n${YELLOW}--- CẤU HÌNH HỆ THỐNG & CÀI ĐẶT DEPENDENCIES ---${NC}"
apt-get update -y
apt-get install -y git curl wget build-essential software-properties-common ufw

# 5. Cài đặt Python 3, Pip và Venv cho Backend
echo -e "\n${YELLOW}--- CÀI ĐẶT PYTHON 3 ---${NC}"
apt-get install -y python3 python3-pip python3-venv

# 6. Cài đặt Node.js v20 (LTS) và PM2 cho Frontend
echo -e "\n${YELLOW}--- CÀI ĐẶT NODE.JS & PM2 ---${NC}"
if ! command -v node &> /dev/null; then
  echo -e "${YELLOW}Đang cài đặt Node.js v20...${NC}"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
else
  echo -e "${GREEN}Node.js đã được cài đặt: $(node -v)${NC}"
fi

if ! command -v pm2 &> /dev/null; then
  echo -e "${YELLOW}Đang cài đặt PM2...${NC}"
  npm install -g pm2
else
  echo -e "${GREEN}PM2 đã được cài đặt.${NC}"
fi

# 7. Cài đặt và cấu hình PostgreSQL
echo -e "\n${YELLOW}--- CÀI ĐẶT & CẤU HÌNH POSTGRESQL ---${NC}"
apt-get install -y postgresql postgresql-contrib
systemctl start postgresql
systemctl enable postgresql

# Tạo User và Database trong Postgres
echo -e "${YELLOW}Đang thiết lập database postgresql...${NC}"
# Kiểm tra user xem đã tồn tại chưa
USER_EXISTS=$(sudo -u postgres psql -t -c "\du" | cut -d \| -f 1 | grep -q 'postgresql'; echo $?)
if [ "$USER_EXISTS" -ne 0 ]; then
  sudo -u postgres psql -c "CREATE USER postgresql WITH PASSWORD 'Thang123456';"
  sudo -u postgres psql -c "ALTER USER postgresql WITH SUPERUSER;"
  echo -e "${GREEN}Đã tạo user 'postgresql' với quyền Superuser.${NC}"
else
  echo -e "${GREEN}User 'postgresql' đã tồn tại.${NC}"
fi

# Kiểm tra database xem đã tồn tại chưa
DB_EXISTS=$(sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw 'thangdz_web'; echo $?)
if [ "$DB_EXISTS" -ne 0 ]; then
  sudo -u postgres psql -c "CREATE DATABASE thangdz_web OWNER postgresql;"
  echo -e "${GREEN}Đã tạo database 'thangdz_web'.${NC}"
else
  echo -e "${GREEN}Database 'thangdz_web' đã tồn tại.${NC}"
fi

# 8. Cấu hình và Chạy Backend (FastAPI)
echo -e "\n${YELLOW}--- CẤU HÌNH & KHỞI CHẠY BACKEND (FASTAPI) ---${NC}"
cd "$PROJECT_DIR/backend"

# Viết file .env cho Backend
if [ -f ".env" ]; then
  echo -e "${YELLOW}Phát hiện file .env của backend đã tồn tại.${NC}"
  read -p "Bạn có muốn ghi đè cấu hình file .env này không? (y/N): " OVERWRITE_ENV
  if [ "$OVERWRITE_ENV" = "y" ] || [ "$OVERWRITE_ENV" = "Y" ]; then
    WRITE_ENV=true
  else
    WRITE_ENV=false
  fi
else
  WRITE_ENV=true
fi

if [ "$WRITE_ENV" = "true" ]; then
  echo -e "Đang ghi cấu hình .env mới cho backend..."
  cat <<EOF > .env
DATABASE_URL=postgresql://postgresql:Thang123456@localhost:5432/thangdz_web
SECRET_KEY=b9000a6e744d2d48bf5b27376c9a997092928502db1bc6c1ec0c1285bf8a48b8
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
ENV=production
CORS_ORIGINS=https://$DOMAIN,https://www.$DOMAIN
EOF
  chown $REAL_USER:$REAL_USER .env
else
  echo -e "${GREEN}Giữ nguyên cấu hình .env hiện tại của backend.${NC}"
fi

# Thiết lập venv và cài đặt thư viện python
if [ -d "venv" ]; then
  echo -e "Xóa venv cũ để tạo mới đồng bộ với VPS..."
  rm -rf venv
fi
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
chown -R $REAL_USER:$REAL_USER venv

# Dừng và gỡ bỏ Systemd service cũ của backend (nếu có) để tránh xung đột cổng
if [ -f "/etc/systemd/system/thangdz-backend.service" ]; then
  echo -e "Đang dừng và xóa Systemd service cũ của backend..."
  systemctl stop thangdz-backend 2>/dev/null || true
  systemctl disable thangdz-backend 2>/dev/null || true
  rm -f /etc/systemd/system/thangdz-backend.service
  systemctl daemon-reload
fi

# Khởi chạy Backend bằng PM2
echo -e "Khởi chạy Backend bằng PM2..."
# Giải phóng cổng 8000 nếu có tiến trình chạy ngầm cũ
if command -v fuser >/dev/null 2>&1; then
  fuser -k 8000/tcp 2>/dev/null || true
elif command -v lsof >/dev/null 2>&1; then
  kill -9 $(lsof -t -i:8000) 2>/dev/null || true
fi

sudo -u $REAL_USER pm2 delete "thangdz-backend" 2>/dev/null || true
sudo -u $REAL_USER pm2 start "$PROJECT_DIR/backend/venv/bin/uvicorn" --name "thangdz-backend" --interpreter none --cwd "$PROJECT_DIR/backend" -- app.main:app --host 127.0.0.1 --port 8000 --root-path /api
echo -e "${GREEN}Dịch vụ backend đã khởi chạy thành công trên cổng 8000 bằng PM2!${NC}"

# 9. Cấu hình và Khởi chạy Website chính (Next.js Frontend)
echo -e "\n${YELLOW}--- KHỞI CHẠY WEBSITE CHÍNH (FRONTEND) ---${NC}"
cd "$PROJECT_DIR/website_thangdz/frontend"

# Thiết lập file .env.local cho client build
echo -e "Thiết lập môi trường build cho website..."
cat <<EOF > .env.local
NEXT_PUBLIC_API_URL=https://$DOMAIN/api
N8N_CHAT_WEBHOOK_URL=https://thangdepzai.devttt.com/webhook/thangdz
EOF
chown $REAL_USER:$REAL_USER .env.local

# Cài đặt dependency & Build
echo -e "Đang cài đặt thư viện & build Next.js (có thể mất 1-2 phút)..."
sudo -u $REAL_USER npm install
sudo -u $REAL_USER npm run build

# Chạy PM2 dưới quyền REAL_USER
echo -e "Khởi chạy Website Frontend bằng PM2..."
sudo -u $REAL_USER pm2 delete "thangdz-frontend" 2>/dev/null || true
sudo -u $REAL_USER pm2 start npm --name "thangdz-frontend" -- start -- -p 3000

# 10. Cấu hình và Khởi chạy Trang Quản Trị (Admin Frontend)
echo -e "\n${YELLOW}--- KHỞI CHẠY TRANG QUẢN TRỊ (ADMIN) ---${NC}"
cd "$PROJECT_DIR/web_quantri_thangdz"

# Thiết lập file .env.local cho admin build
echo -e "Thiết lập môi trường build cho trang quản trị..."
cat <<EOF > .env.local
NEXT_PUBLIC_API_URL=https://$DOMAIN/api
EOF
chown $REAL_USER:$REAL_USER .env.local

# Cài đặt dependency & Build
echo -e "Đang cài đặt thư viện & build trang quản trị (có thể mất 1-2 phút)..."
sudo -u $REAL_USER npm install
sudo -u $REAL_USER npm run build

# Chạy PM2 dưới quyền REAL_USER
echo -e "Khởi chạy Admin Frontend bằng PM2..."
sudo -u $REAL_USER pm2 delete "thangdz-admin" 2>/dev/null || true
sudo -u $REAL_USER pm2 start npm --name "thangdz-admin" -- start -- -p 3001

# Lưu trạng thái PM2 và cấu hình startup để tự chạy lại khi VPS reboot
echo -e "Thiết lập PM2 khởi động cùng hệ thống..."
if [ "$REAL_USER" = "root" ]; then
  pm2 startup systemd -u root --hp /root
  pm2 save
else
  # Tạo lệnh startup cho user thường
  pm2_startup_cmd=$(env PATH=$PATH:/usr/bin pm2 startup systemd -u $REAL_USER --hp /home/$REAL_USER | grep "sudo env")
  if [ -n "$pm2_startup_cmd" ]; then
    eval $pm2_startup_cmd
  fi
  sudo -u $REAL_USER pm2 save
fi

# 11. Cài đặt và cấu hình Nginx
echo -e "\n${YELLOW}--- CẤU HÌNH NGINX REVERSE PROXY ---${NC}"
apt-get install -y nginx

# Tạo File cấu hình Nginx
cat <<EOF > /etc/nginx/sites-available/thangdz.conf
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # 1. Main Website Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 2. Admin Dashboard (basePath: /admin)
    location /admin {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # 3. Backend API (FastAPI root_path: /api)
    location = /api {
        return 307 /api/;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Prefix /api;
        client_max_body_size 50M;
    }
}
EOF

# Kích hoạt cấu hình mới và hủy default config
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/thangdz.conf /etc/nginx/sites-enabled/

# Reload Nginx
systemctl restart nginx
echo -e "${GREEN}Cấu hình Nginx reverse proxy thành công!${NC}"

# 12. Cấu hình Firewall (UFW)
echo -e "\n${YELLOW}--- MỞ FIREWALL (UFW) ---${NC}"
ufw allow OpenSSH
ufw allow 'Nginx Full'
echo "y" | ufw enable
ufw status

# 13. Cài đặt SSL Let's Encrypt qua Certbot
echo -e "\n${YELLOW}--- CÀI ĐẶT SSL LET'S ENCRYPT ---${NC}"
apt-get install -y certbot python3-certbot-nginx

echo -e "Đang đăng ký chứng chỉ SSL cho các tên miền: $DOMAIN, www.$DOMAIN..."
# Chạy Certbot tự động cấu hình Nginx
certbot --nginx \
  -d $DOMAIN \
  -d www.$DOMAIN \
  --non-interactive \
  --agree-tos \
  --email $EMAIL \
  --redirect

if [ $? -eq 0 ]; then
  echo -e "${GREEN}Đã cài đặt chứng chỉ SSL Let's Encrypt thành công cho tất cả các tên miền!${NC}"
else
  echo -e "${RED}Cảnh báo: Có lỗi xảy ra trong quá trình cài đặt SSL. Vui lòng kiểm tra lại cấu hình DNS của bạn đã trỏ đúng về IP của VPS này chưa, sau đó chạy lại lệnh:${NC}"
  echo -e "  sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"
fi

# Kết thúc triển khai
echo -e "\n${BLUE}======================================================================${NC}"
echo -e "${GREEN}           QUÁ TRÌNH TRIỂN KHAI DỰ ÁN HOÀN TẤT THÀNH CÔNG!           ${NC}"
echo -e "${BLUE}======================================================================${NC}"
echo -e "Bạn có thể truy cập các đường dẫn sau:"
echo -e " 1. Trang chủ chính thức:  ${GREEN}https://$DOMAIN${NC} (hoặc https://www.$DOMAIN)"
echo -e " 2. Trang quản trị Admin:  ${GREEN}https://$DOMAIN/admin${NC}"
echo -e " 3. Tài liệu API Backend:  ${GREEN}https://$DOMAIN/api/docs${NC}"
echo -e " 4. Trạng thái các dịch vụ:${YELLOW}"
sudo -u $REAL_USER pm2 status
echo -e "${NC}======================================================================"
echo -e "${YELLOW}Gợi ý:${NC} Để kiểm tra logs hệ thống, bạn có thể dùng các lệnh:"
echo -e " - Logs Frontend/Admin/Backend: ${BLUE}pm2 logs${NC}"
echo -e " - Logs Backend riêng:         ${BLUE}pm2 logs thangdz-backend${NC}"
echo -e "======================================================================"
