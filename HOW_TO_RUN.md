# HƯỚNG DẪN KHỞI CHẠY DỰ ÁN THANGDZ.COM_FULL_01072026 (HOW TO RUN)

Dự án bao gồm 3 phần chính chạy độc lập trực tiếp trên môi trường local (không dùng Docker).

---

## 1. KHỞI CHẠY BACKEND (FASTAPI) - CỔNG 8000

* **Yêu cầu:** Máy đã cài sẵn Python và cơ sở dữ liệu PostgreSQL đang chạy.
* **Các bước thực hiện:**

1. Mở Terminal mới từ thư mục gốc của dự án (`THANGDZ.COM_FULL_01072026`) và di chuyển đến thư mục backend:
   ```powershell
   cd backend
   ```

2. Tạo môi trường ảo Python (Venv):
   ```powershell
   python -m venv venv
   ```

3. Kích hoạt môi trường ảo:
   * Trên **PowerShell**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * Trên **CMD / Command Prompt**:
     ```cmd
     .\venv\Scripts\activate.bat
     ```

4. Cài đặt các thư viện cần thiết:
   ```powershell
   pip install -r requirements.txt
   ```

5. Khởi chạy API Server với Uvicorn:
   ```powershell
   uvicorn app.main:app --reload
   ```
   * *Hệ thống sẽ tự động tạo cơ sở dữ liệu `thangdz_web` nếu chưa tồn tại, tự động đồng bộ hóa bảng biểu và nạp dữ liệu mẫu (seed database).*
   * Tài liệu API tương tác (Swagger UI): `http://localhost:8000/docs`

---

## 2. KHỞI CHẠY WEBSITE CHÍNH FRONTEND (NEXT.JS) - CỔNG 3000

* **Yêu cầu:** Máy đã cài đặt Node.js.
* **Các bước thực hiện:**

1. Mở Terminal mới từ thư mục gốc của dự án (`THANGDZ.COM_FULL_01072026`) và di chuyển đến thư mục frontend của website chính:
   ```powershell
   cd website_thangdz\frontend
   ```

2. Cài đặt các gói thư viện Node.js:
   ```powershell
   npm install
   ```

3. Khởi chạy máy chủ phát triển (Development Server):
   ```powershell
   npm run dev
   ```
   * Website chính sẽ chạy tại địa chỉ: `http://localhost:3000`

---

## 3. KHỞI CHẠY TRANG QUẢN TRỊ ADMIN (NEXT.JS) - CỔNG 3001

* **Yêu cầu:** Máy đã cài đặt Node.js.
* **Các bước thực hiện:**

1. Mở Terminal mới từ thư mục gốc của dự án (`THANGDZ.COM_FULL_01072026`) và di chuyển đến thư mục quản trị:
   ```powershell
   cd web_quantri_thangdz
   ```

2. Cài đặt các gói thư viện Node.js:
   ```powershell
   npm install
   ```

3. Khởi chạy máy chủ phát triển:
   ```powershell
   npm run dev
   ```
   * Trang quản trị Admin Dashboard sẽ chạy tại địa chỉ: `http://localhost:3001` (hoặc cổng khác nếu cổng 3000 đang được dùng bởi website chính).
