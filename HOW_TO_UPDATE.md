# HƯỚNG DẪN CẬP NHẬT MÃ NGUỒN DỰ ÁN (HOW TO UPDATE)

Tài liệu này hướng dẫn cách cập nhật mã nguồn (code) của dự án **thangdz.com** lên VPS sau khi bạn đã sửa đổi code dưới máy tính cá nhân. Có hai cách tiếp cận chính: **Cập nhật nhanh qua Git (Khuyên dùng)** và **Xây dựng hệ thống tự động tải Zip qua trang Admin (Tính năng nâng cao)**.

---

## CÁCH 1: CẬP NHẬT QUA GIT & SCRIPT (ĐƠN GIẢN & AN TOÀN NHẤT)

Đây là quy trình chuẩn mà các lập trình viên thường dùng để deploy lại code mới.

### Bước 1: Đẩy code mới lên GitHub từ máy cá nhân
Sau khi bạn đã sửa code và chạy thử thành công ở local, hãy đẩy code lên kho chứa GitHub của bạn:
```bash
git add .
git commit -m "Cập nhật tính năng mới / Sửa lỗi"
git push origin main
```

### Bước 2: Kéo code mới về trên VPS
Kết nối SSH vào VPS của bạn, di chuyển vào thư mục dự án và kéo code mới nhất về:
```bash
cd /thư_mục_chứa_dự_án_trên_vps/thangdz.com
git pull
```

### Bước 3: Thực hiện cập nhật các dịch vụ
Bạn có 2 lựa chọn để khởi động lại dự án với code mới:

#### Lựa chọn A: Chạy lại file deploy có sẵn (Tự động nhưng mất thời gian build lại toàn bộ)
```bash
sudo ./deploy.sh
```
*Lưu ý: Script này sẽ chạy lại cả phần cấu hình hệ thống nên sẽ mất 2-3 phút.*

#### Lựa chọn B: Tạo và sử dụng file script cập nhật nhanh `update.sh` (Nhanh hơn)
Tạo một file có tên `update.sh` nằm cùng cấp thư mục với `deploy.sh` trên VPS với nội dung sau:
```bash
#!/bin/bash
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo "=== ĐANG BẮT ĐẦU CẬP NHẬT DỰ ÁN ==="

# 1. Cập nhật Backend
echo "-> Cập nhật Backend FastAPI..."
cd website_thangdz/backend
./venv/bin/pip install -r requirements.txt
sudo systemctl restart thangdz-backend

# 2. Cập nhật Website Frontend
echo "-> Build & Restart Website Frontend..."
cd ../frontend
npm install
npm run build
pm2 restart thangdz-frontend

# 3. Cập nhật Trang Quản Trị Admin
echo "-> Build & Restart Trang Admin..."
cd ../../web_quantri_thangdz
npm install
npm run build
pm2 restart thangdz-admin

echo "=== CẬP NHẬT HOÀN TẤT VÀ THÀNH CÔNG! ==="
```
Cấp quyền chạy cho file này trên VPS:
```bash
chmod +x update.sh
```
Mỗi lần cập nhật code, bạn chỉ cần gõ:
```bash
./update.sh
```

---

## CÁCH 2: HỆ THỐNG TỰ ĐỘNG CẬP NHẬT (SELF-UPDATE) QUA TRANG ADMIN

Đây là giải pháp nâng cao giống như các công cụ CMS (WordPress), cho phép cập nhật phiên bản mới chỉ bằng một nút bấm trên trang Quản trị Admin (`https://thangdz.com/admin`).

### Sơ đồ hoạt động (Workflow):
```
[Máy cá nhân] -> Nén code (.zip) + Tạo file version.json -> Upload lên GitHub Releases/Cloudflare R2
                                                                   |
[Trang Admin] -> Bấm "Kiểm tra cập nhật" -> So sánh phiên bản <----+
     |
     +---------> Bấm "Cập nhật" -> Gọi API Backend -> Tải file .zip -> Giải nén ghi đè -> Chạy script update
```

### Các bước thiết lập chi tiết:

#### 1. Chuẩn bị nơi lưu trữ phiên bản mới (Storage)
Khi có phiên bản mới, bạn đóng gói code thành file `update.zip` và viết file `version.json` để mô tả phiên bản mới:
```json
{
  "version": "2.0.0",
  "download_url": "https://đường-dẫn-lưu-trữ-của-bạn/update.zip",
  "changelog": "- Cập nhật giao diện mới đẹp hơn\n- Sửa một số lỗi bảo mật"
}
```
Upload cả 2 file này lên **GitHub Releases** hoặc dịch vụ lưu trữ đám mây như **Cloudflare R2 / AWS S3**.

#### 2. Xây dựng giao diện trên Frontend Admin (`web_quantri_thangdz`)
Tạo một màn hình **"Cập nhật hệ thống"**:
* Hiển thị phiên bản hiện tại (lấy từ cấu hình hệ thống).
* Gọi API của Backend để lấy file `version.json` từ kho lưu trữ.
* Nếu phiên bản online mới hơn phiên bản hiện tại, hiển thị nút **"Cập nhật lên phiên bản [mới]"**.
* Khi nhấn nút, gọi API gửi yêu cầu cập nhật tới Backend.

#### 3. Xây dựng API xử lý trên Backend (`website_thangdz/backend`)
Tạo endpoint API (ví dụ: `/api/system/update`) để xử lý các việc sau chạy dưới dạng tác vụ ngầm (Background Task):
* Tải file `.zip` từ `download_url` về thư mục tạm trên VPS.
* Thực hiện giải nén (unzip) đè lên thư mục hiện tại của dự án.
* Chạy lệnh shell script `update.sh` để hệ thống tự động build Next.js và restart lại các service (PM2 & FastAPI).

---

## LỆNH THEO DÕI LOGS VÀ TRẠNG THÁI SAU KHI UPDATE
Để đảm bảo code chạy mượt mà sau khi cập nhật, bạn có thể kiểm tra trạng thái dịch vụ trên VPS bằng các lệnh:

* **Xem trạng thái chạy của Frontend & Admin:**
  ```bash
  pm2 status
  ```
* **Xem logs thời gian thực của Frontend:**
  ```bash
  pm2 logs thangdz-frontend
  ```
* **Xem logs thời gian thực của Admin:**
  ```bash
  pm2 logs thangdz-admin
  ```
* **Xem logs thời gian thực của Backend:**
  ```bash
  sudo journalctl -u thangdz-backend -f -n 100
  ```
