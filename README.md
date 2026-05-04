# LightOnOCR

Windows desktop app — OCR PDF bằng model **LightOnOCR-2-1B-ONNX** (phiên bản lượng tử hóa int4 chạy local siêu nhẹ trên CPU).

## Cài đặt & Chạy

```powershell
# 1. Tạo venv (nếu chưa có)
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

*(Các thư viện chính bao gồm `onnxruntime`, `transformers`, `pillow`, `pypdfium2`, `tkinterdnd2`...)*

```powershell
# 3. Chạy app
python main.py
```

> **Lần đầu chạy OCR**: Model sẽ tự động tải về (~755MB, lưu vào HuggingFace cache). Lần sau khởi động sẽ tải ngay lập tức.

## Build .exe (PyInstaller)

```powershell
pip install pyinstaller
pyinstaller LightOnOCR.spec
# Output: dist\LightOnOCR\LightOnOCR.exe
```

## Tạo installer (Inno Setup)

1. Cài [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. Build `.exe` trước
3. Mở `installer\setup.iss` → Compile
4. Output: `dist\installer\LightOnOCR_Setup_v1.1.0.exe`

## Cấu trúc

```
ocr/
├── main.py              # GUI chính (tkinter dark theme)
├── ocr_engine.py        # Model ONNX wrapper (CPUExecutionProvider)
├── pdf_processor.py     # Xử lý PDF → PIL images (pypdfium2)
├── startup_manager.py   # Quản lý khởi động cùng Windows (Registry)
├── config.py            # Quản lý preset và cấu hình
├── requirements.txt     # Danh sách thư viện
├── LightOnOCR.spec      # File cấu hình build PyInstaller
├── installer/
│   └── setup.iss        # Cấu hình Inno Setup
└── assets/
    └── icon.ico         # Icon ứng dụng
```

## Output format

Model trả về **Markdown** — headings, tables, LaTeX math được giữ nguyên định dạng.
File kết quả mặc định được hiển thị dưới dạng thô trên app để tiện sao chép, và có thể lưu file `.md` bằng hộp thoại chọn thư mục.

## Tính năng nổi bật

- Drag & drop PDF trực tiếp vào màn hình.
- Chọn phạm vi trang OCR (từ trang → đến trang).
- Thanh tiến trình chi tiết hiển thị số trang đã xử lý.
- Chọn tốc độ (Preset: Chất lượng, Nhanh, Turbo) để cân bằng giữa thời gian và độ phân giải ảnh quét.
- Lưu file Markdown `.md` với hộp thoại chọn nơi lưu hoặc Copy nhanh vào Clipboard.
- Chế độ Dark Theme tối giản, chống mỏi mắt.
- Tự động chạy cùng Windows (Toggle qua Registry).
