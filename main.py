"""
main.py — LightOnOCR Windows Desktop App
GUI: tkinter + tkinterdnd2 (drag & drop)
"""
import logging
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import markdown
from tkhtmlview import HTMLScrolledText

# Thêm thư mục hiện tại vào sys.path (cho PyInstaller)
if getattr(sys, "frozen", False):
  sys.path.insert(0, sys._MEIPASS)  # type: ignore
else:
  sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
  level=logging.WARNING,
  format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
  datefmt="%H:%M:%S",
)
for _n in ("main", "ocr_engine", "pdf_processor"):
  logging.getLogger(_n).setLevel(logging.INFO)
log = logging.getLogger("main")

from config import APP_NAME, APP_VERSION, MODEL_ID, load_config, save_config
import startup_manager
log.info("App starting: %s v%s", APP_NAME, APP_VERSION)

# ── Màu sắc (Theme dịu mắt) ──────────────────────────────────
BG_DARK = "#1E1E1E"        # Nền chính
BG_PANEL = "#252526"       # Nền sidebar
BG_CARD = "#2D2D30"        # Nền khung nhỏ
ACCENT = "#0E639C"         # Xanh dương đậm (nút bấm)
ACCENT_HOVER = "#1177BB"   # Xanh dương nhạt (hover)
ACCENT2 = "#4EC9B0"        # Xanh ngọc (highlight chữ)
TEXT_PRIMARY = "#D4D4D4"   # Chữ chính (xám nhạt)
TEXT_SECONDARY = "#CCCCCC" # Chữ phụ
TEXT_MUTED = "#858585"     # Chữ mờ
BORDER = "#3E3E42"         # Viền
SUCCESS = "#4EC9B0"        # Thành công
WARNING = "#D7BA7D"        # Cảnh báo
ERROR_COLOR = "#F48771"    # Lỗi (đỏ nhạt, không chói)


class App(tk.Tk):
  def __init__(self) -> None:
    super().__init__()
    self.cfg = load_config()
    self.pdf_path: str | None = None
    self.ocr_results: list[str] = []
    self._ocr_thread: threading.Thread | None = None

    self._setup_window()
    self._build_ui()
    self._apply_theme()

  # ── Window setup ──────────────────────────────────────────
  def _setup_window(self) -> None:
    self.title(f"{APP_NAME} v{APP_VERSION}")
    self.geometry("1100x720")
    self.minsize(800, 560)
    self.configure(bg=BG_DARK)

    # Icon (nếu có)
    ico = Path(__file__).parent / "assets" / "icon.ico"
    if ico.exists():
      self.iconbitmap(str(ico))

    self.protocol("WM_DELETE_WINDOW", self._on_close)

  # ── UI Build ──────────────────────────────────────────────
  def _build_ui(self) -> None:
    self._build_main()
    self._build_statusbar()
  def _build_main(self) -> None:
    main = tk.Frame(self, bg=BG_DARK)
    main.pack(fill=tk.BOTH, expand=True, padx=16, pady=(12, 0))

    # ── Left panel ──
    left = tk.Frame(main, bg=BG_DARK, width=320)
    left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
    left.pack_propagate(False)

    # Drop zone
    self._build_dropzone(left)

    # Page range
    self._build_page_range(left)

    # Speed preset
    self._build_speed_preset(left)

    # Action buttons
    self._build_action_buttons(left)

    # Progress
    self._build_progress(left)

    # ── Right panel ──
    right = tk.Frame(main, bg=BG_DARK)
    right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    self._build_output_panel(right)

  def _build_dropzone(self, parent: tk.Frame) -> None:
    self.drop_frame = tk.Frame(
      parent, bg=BG_CARD, bd=0,
      highlightbackground=BORDER, highlightthickness=2,
    )
    self.drop_frame.pack(fill=tk.X, pady=(0, 12))

    inner = tk.Frame(self.drop_frame, bg=BG_CARD)
    inner.pack(fill=tk.X, padx=12, pady=12)

    tk.Label(
      inner, text="📄", font=("Segoe UI Emoji", 16),
      bg=BG_CARD, fg=TEXT_SECONDARY,
    ).pack(side=tk.LEFT, padx=(0, 8))

    self.file_label = tk.Label(
      inner, text="Kéo thả PDF hoặc chọn file",
      font=("Segoe UI", 9), fg=TEXT_PRIMARY, bg=BG_CARD,
      anchor=tk.W,
    )
    self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    self._make_btn(inner, "Chọn", self._browse_file, style="secondary").pack(side=tk.RIGHT)

    self.drop_frame.bind("<Button-1>", lambda e: self._browse_file())
    self._bind_drag_drop()

  def _bind_drag_drop(self) -> None:
    """Try tkinterdnd2 drag & drop, fallback nếu không có."""
    try:
      import tkinterdnd2  # noqa: F401
      self.drop_frame.drop_target_register("DND_Files")  # type: ignore
      self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore
    except Exception:
      pass

  def _build_page_range(self, parent: tk.Frame) -> None:
    card = self._card(parent, "Phạm vi trang")
    card.pack(fill=tk.X, pady=(0, 12))

    row = tk.Frame(card, bg=BG_CARD)
    row.pack(fill=tk.X, padx=16, pady=(0, 12))

    tk.Label(row, text="Từ trang:", font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_CARD).pack(side=tk.LEFT)
    self.page_from = tk.StringVar(value="1")
    tk.Entry(
      row, textvariable=self.page_from, width=5,
      bg=BG_DARK, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
      relief=tk.FLAT, font=("Segoe UI", 10),
    ).pack(side=tk.LEFT, padx=6)

    tk.Label(row, text="đến:", font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_CARD).pack(side=tk.LEFT)
    self.page_to = tk.StringVar(value="")
    tk.Entry(
      row, textvariable=self.page_to, width=5,
      bg=BG_DARK, fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
      relief=tk.FLAT, font=("Segoe UI", 10),
    ).pack(side=tk.LEFT, padx=6)

    tk.Label(row, text="(trống = tất cả)", font=("Segoe UI", 8), fg=TEXT_MUTED, bg=BG_CARD).pack(side=tk.LEFT)

    self.total_pages_label = tk.Label(
      card, text="", font=("Segoe UI", 9), fg=ACCENT2, bg=BG_CARD,
    )
    self.total_pages_label.pack(padx=16, pady=(0, 12), anchor=tk.W)

  def _build_speed_preset(self, parent: tk.Frame) -> None:
    from config import SPEED_PRESETS
    card = self._card(parent, "Tốc độ")
    card.pack(fill=tk.X, pady=(0, 12))

    self._preset_var = tk.StringVar(value=self.cfg.get("speed_preset", "quality"))

    def on_preset_change(*_):
      preset = self._preset_var.get()
      p = SPEED_PRESETS.get(preset, SPEED_PRESETS["quality"])
      self.cfg["speed_preset"] = preset
      self.cfg["dpi_scale"] = p["dpi_scale"]
      self.cfg["max_longest_dim"] = p["max_longest_dim"]
      self.cfg["max_new_tokens"] = p["max_new_tokens"]
      save_config(self.cfg)

    self._preset_var.trace_add("write", on_preset_change)

    row = tk.Frame(card, bg=BG_CARD)
    row.pack(fill=tk.X, padx=16, pady=(0, 12))
    for label, val in [("Chất lượng", "quality"), ("Nhanh", "fast"), ("Turbo", "turbo")]:
      tk.Radiobutton(
        row, text=label, variable=self._preset_var, value=val,
        bg=BG_CARD, fg=TEXT_PRIMARY, selectcolor=BG_DARK,
        activebackground=BG_CARD, activeforeground=TEXT_PRIMARY,
        font=("Segoe UI", 9), cursor="hand2",
      ).pack(side=tk.LEFT, padx=4)

  def _build_action_buttons(self, parent: tk.Frame) -> None:
    card = self._card(parent, "Thao tác")
    card.pack(fill=tk.X, pady=(0, 12))

    self.run_btn = self._make_btn(card, "▶  Bắt đầu OCR", self._start_ocr, style="primary")
    self.run_btn.pack(fill=tk.X, padx=16, pady=(4, 6))
    self.run_btn.configure(state=tk.DISABLED)

    self.stop_btn = self._make_btn(card, "⏹  Dừng", self._stop_ocr, style="danger")
    self.stop_btn.pack(fill=tk.X, padx=16, pady=(0, 6))
    self.stop_btn.configure(state=tk.DISABLED)

    btn_row = tk.Frame(card, bg=BG_CARD)
    btn_row.pack(fill=tk.X, padx=16, pady=(0, 12))

    self._make_btn(btn_row, "💾 Lưu .docx", self._save_docx, style="secondary").pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                padx=(0, 4))
    self._make_btn(btn_row, "📋 Copy", self._copy_text, style="secondary").pack(side=tk.LEFT, expand=True, fill=tk.X,
                                                                                padx=(4, 0))

  def _build_progress(self, parent: tk.Frame) -> None:
    card = self._card(parent, "Tiến trình")
    card.pack(fill=tk.X, pady=(0, 12))

    self.progress_var = tk.DoubleVar(value=0.0)
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
      "OCR.Horizontal.TProgressbar",
      troughcolor=BG_DARK, background=ACCENT,
      bordercolor=BORDER, lightcolor=ACCENT, darkcolor=ACCENT,
    )
    pb = ttk.Progressbar(
      card, variable=self.progress_var, maximum=100,
      style="OCR.Horizontal.TProgressbar",
    )
    pb.pack(fill=tk.X, padx=16, pady=(4, 6))
    self.progress_bar = pb

    self.progress_label = tk.Label(
      card, text="Sẵn sàng",
      font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_CARD,
    )
    self.progress_label.pack(padx=16, pady=(0, 12), anchor=tk.W)

  def _set_progress_mode(self, mode: str) -> None:
    """Switch progressbar: 'indeterminate' (download) or 'determinate' (per-page)."""
    if mode == "indeterminate":
      self.progress_bar.configure(mode="indeterminate")
      self.progress_bar.start(12)  # pulse every 12ms
    else:
      self.progress_bar.stop()
      self.progress_bar.configure(mode="determinate")

  def _build_output_panel(self, parent: tk.Frame) -> None:
    # Header
    hdr = tk.Frame(parent, bg=BG_DARK)
    hdr.pack(fill=tk.X, pady=(0, 8))

    tk.Label(
      hdr, text="Kết quả OCR", font=("Segoe UI", 12, "bold"),
      fg=TEXT_PRIMARY, bg=BG_DARK,
    ).pack(side=tk.LEFT)

    self.char_count_label = tk.Label(
      hdr, text="", font=("Segoe UI", 9), fg=TEXT_MUTED, bg=BG_DARK,
    )
    self.char_count_label.pack(side=tk.RIGHT, padx=4)

    # Page tabs
    self.tab_frame = tk.Frame(parent, bg=BG_DARK)
    self.tab_frame.pack(fill=tk.X, pady=(0, 6))

    # HTML rendered area for Markdown display
    text_container = tk.Frame(parent, bg=BORDER, bd=1)
    text_container.pack(fill=tk.BOTH, expand=True)

    self.html_view = HTMLScrolledText(
      text_container,
      background=BG_PANEL,
      padx=16, pady=16,
    )
    self.html_view.pack(fill=tk.BOTH, expand=True)
    self.html_view.set_html("<p style='color:#858585;font-family:Segoe UI;'>Kết quả sẽ hiển thị ở đây...</p>")

  def _build_statusbar(self) -> None:
    bar = tk.Frame(self, bg=BG_PANEL, height=28)
    bar.pack(fill=tk.X, side=tk.BOTTOM)
    bar.pack_propagate(False)

    self.status_label = tk.Label(
      bar, text=f"{APP_NAME} sẵn sàng",
      font=("Segoe UI", 9), fg=TEXT_SECONDARY, bg=BG_PANEL, anchor=tk.W,
    )
    self.status_label.pack(side=tk.LEFT, padx=12, pady=4)

    # Device info badge
    self._show_device_badge(bar)

    # Startup toggle
    self._startup_var = tk.BooleanVar(value=startup_manager.is_startup_enabled())
    cb = tk.Checkbutton(
      bar, text="Chạy khi khởi động Windows",
      variable=self._startup_var, command=self._toggle_startup,
      bg=BG_PANEL, fg=TEXT_SECONDARY, selectcolor=BG_DARK,
      activebackground=BG_PANEL, activeforeground=TEXT_PRIMARY,
      font=("Segoe UI", 9), cursor="hand2",
    )
    cb.pack(side=tk.RIGHT, padx=12)

  def _show_device_badge(self, parent: tk.Widget) -> None:
    try:
      from ocr_engine import get_device_info
      info = get_device_info()
      dev = info["device"]
      if dev == "cuda":
        vram = info.get("vram_gb", "?")
        label = f"🟢 GPU: {info['name']} ({vram}GB VRAM)"
        color = SUCCESS
      elif dev == "mps":
        label = "🟢 Apple MPS"
        color = SUCCESS
      else:
        label = "🟡 CPU mode"
        color = WARNING
    except Exception:
      label = "⚪ Device: unknown"
      color = TEXT_MUTED

    tk.Label(
      parent, text=label,
      font=("Segoe UI", 9), fg=color, bg=BG_PANEL,
    ).pack(side=tk.RIGHT, padx=16)

  # ── Widget helpers ────────────────────────────────────────
  def _card(self, parent: tk.Widget, title: str) -> tk.Frame:
    frame = tk.Frame(parent, bg=BG_CARD, bd=0,
                     highlightbackground=BORDER, highlightthickness=1)
    tk.Label(
      frame, text=title, font=("Segoe UI", 9, "bold"),
      fg=TEXT_SECONDARY, bg=BG_CARD,
    ).pack(anchor=tk.W, padx=16, pady=(10, 6))
    return frame

  def _make_btn(
    self, parent: tk.Widget, text: str, cmd, style: str = "primary"
  ) -> tk.Button:
    styles = {
      "primary": (ACCENT, TEXT_PRIMARY, ACCENT_HOVER),
      "secondary": (BG_DARK, TEXT_SECONDARY, BG_CARD),
      "ghost": (BG_PANEL, TEXT_SECONDARY, BG_CARD),
      "danger": (ERROR_COLOR, TEXT_PRIMARY, "#FF3B36"),
    }
    bg, fg, hover = styles.get(style, styles["primary"])
    btn = tk.Button(
      parent, text=text, command=cmd,
      bg=bg, fg=fg, activebackground=hover, activeforeground=TEXT_PRIMARY,
      disabledforeground="#D4D4D4",
      relief=tk.FLAT, bd=0, padx=14, pady=7,
      font=("Segoe UI", 10), cursor="hand2",
    )
    btn.bind("<Enter>", lambda e: btn.configure(bg=hover) if btn['state'] != tk.DISABLED else None)
    btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn

  def _apply_theme(self) -> None:
    pass  # Theme already applied via constants

  # ── Event handlers ────────────────────────────────────────
  def _browse_file(self) -> None:
    path = filedialog.askopenfilename(
      title="Chọn file PDF",
      filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
    )
    if path:
      self._load_pdf(path)

  def _on_drop(self, event) -> None:
    path = event.data.strip().strip("{}")
    if path.lower().endswith(".pdf"):
      self._load_pdf(path)
    else:
      messagebox.showwarning("Lỗi", "Chỉ hỗ trợ file PDF!")

  def _load_pdf(self, path: str) -> None:
    self.pdf_path = path
    name = Path(path).name

    try:
      from pdf_processor import get_page_count
      total = get_page_count(path)
      self.file_label.configure(text=name, fg=ACCENT2)
      self.total_pages_label.configure(text=f"📄 {total} trang")
      self.page_to.set(str(total))
      self.run_btn.configure(state=tk.NORMAL)
      self._set_status(f"Đã tải: {name} ({total} trang)")
    except Exception as e:
      messagebox.showerror("Lỗi", f"Không đọc được PDF:\n{e}")

  def _start_ocr(self) -> None:
    if not self.pdf_path:
      return

    self.run_btn.configure(state=tk.DISABLED)
    self.stop_btn.configure(state=tk.NORMAL)
    self._stop_flag = False
    self.ocr_results = []
    self._clear_output()
    self._clear_tabs()
    self._set_progress_mode("indeterminate")
    self._ocr_start_time = time.time()

    self._ocr_thread = threading.Thread(target=self._run_ocr_worker, daemon=True)
    self._ocr_thread.start()

  def _run_ocr_worker(self) -> None:
    try:
      from pdf_processor import pdf_to_images, get_page_count
      import ocr_engine

      total = get_page_count(self.pdf_path)

      try:
        p_from = max(1, int(self.page_from.get() or "1")) - 1
        p_to = min(total, int(self.page_to.get() or str(total)))
      except ValueError:
        p_from, p_to = 0, total

      self.ocr_results = [""] * total
      model_id = self.cfg.get("model_id", MODEL_ID)

      def _status(msg: str) -> None:
        self.after(0, self._set_status, msg)
        self.after(0, self.progress_label.configure, {"text": msg})

      page_gen = pdf_to_images(
        self.pdf_path,
        scale=self.cfg["dpi_scale"],
        max_longest_dim=self.cfg["max_longest_dim"],
      )

      done = 0
      for idx, img in page_gen:
        if getattr(self, "_stop_flag", False):
          break
        if idx < p_from or idx >= p_to:
          continue

        is_first = (done == 0)
        text = ocr_engine.ocr_page(
          img, model_id, self.cfg["max_new_tokens"],
          status_callback=_status if is_first else None,
        )

        if is_first:
          self.after(0, self._set_progress_mode, "determinate")

        self.ocr_results[idx] = text
        done += 1
        self.after(0, self._append_page_result, idx, text)
        self._update_progress(done, p_to - p_from, f"OCR trang {idx + 1}/{total}…")

      self.after(0, self._on_ocr_done)
    except Exception as e:
      log.exception("OCR error")
      self.after(0, lambda: messagebox.showerror("Lỗi OCR", str(e)))
      self.after(0, self._on_ocr_done)

  def _stop_ocr(self) -> None:
    self._stop_flag = True
    self._set_status("Đang dừng…")

  def _on_ocr_done(self) -> None:
    self.run_btn.configure(state=tk.NORMAL if self.pdf_path else tk.DISABLED)
    self.stop_btn.configure(state=tk.DISABLED)
    self._update_progress(100, 100, "Hoàn thành!")
    self._set_status("OCR xong!")

  def _append_page_result(self, page_idx: int, text: str) -> None:
    self._add_tab(page_idx, text)
    self._update_char_count()

  def _add_tab(self, page_idx: int, text: str) -> None:
    page_num = page_idx + 1

    def show_this():
      self._show_text(text)
      # Highlight active tab
      for btn in self.tab_frame.winfo_children():
        btn.configure(bg=BG_CARD, fg=TEXT_SECONDARY)
      tab_btn.configure(bg=ACCENT, fg=TEXT_PRIMARY)

    tab_btn = tk.Button(
      self.tab_frame,
      text=f"Trang {page_num}",
      command=show_this,
      bg=BG_CARD, fg=TEXT_SECONDARY,
      relief=tk.FLAT, padx=10, pady=4,
      font=("Segoe UI", 9), cursor="hand2",
    )
    tab_btn.pack(side=tk.LEFT, padx=(0, 4))
    # Auto-show chỉ trang đầu tiên
    if len(self.tab_frame.winfo_children()) == 1:
      show_this()

  def _clear_tabs(self) -> None:
    for w in self.tab_frame.winfo_children():
      w.destroy()

  def _show_text(self, text: str) -> None:
    html = self._md_to_html(text)
    self.html_view.set_html(html)
    self._update_char_count()

  def _md_to_html(self, md_text: str) -> str:
    """Convert markdown to styled HTML for the viewer."""
    body = markdown.markdown(
      md_text,
      extensions=["tables", "fenced_code", "nl2br"],
    )
    return (
      f"<div style='color:{TEXT_PRIMARY};font-family:Segoe UI,sans-serif;"
      f"font-size:13px;line-height:1.6;'>"
      f"{body}</div>"
    )

  def _clear_output(self) -> None:
    self.html_view.set_html("")
    self.char_count_label.configure(text="")

  def _update_char_count(self) -> None:
    total_chars = sum(len(t) for t in self.ocr_results)
    if total_chars:
      self.char_count_label.configure(text=f"{total_chars:,} ký tự")

  # ── Progress & Status ─────────────────────────────────────
  def _update_progress(self, done: int, total: int, msg: str) -> None:
    pct = (done / total * 100) if total else 0
    self.after(0, lambda: self.progress_var.set(pct))
    self.after(0, lambda: self.progress_label.configure(text=msg))
    self.after(0, lambda: self._set_status(msg))

  def _set_status(self, msg: str) -> None:
    self.status_label.configure(text=msg)

  # ── Save / Copy ───────────────────────────────────────────
  def _get_full_text(self) -> str:
    pages = [t for t in self.ocr_results if t]
    return "\n\n---\n\n".join(pages)

  def _save_docx(self) -> None:
    text = self._get_full_text()
    if not text:
      messagebox.showinfo("Thông báo", "Chưa có kết quả OCR!")
      return

    default_name = (Path(self.pdf_path).stem if self.pdf_path else "output") + "_ocr.docx"
    out_dir = self.cfg.get("output_dir", str(Path.home() / "Documents"))
    path = filedialog.asksaveasfilename(
      defaultextension=".docx",
      filetypes=[("Word Document", "*.docx"), ("All", "*.*")],
      initialdir=out_dir,
      initialfile=default_name,
    )
    if path:
      from docx_exporter import md_to_docx
      try:
        md_to_docx(text, path)
        self._set_status(f"Đã lưu: {path}")
      except Exception as e:
        log.exception("DOCX save error")
        messagebox.showerror("Lỗi", f"Không thể lưu DOCX:\n{e}")

  def _copy_text(self) -> None:
    text = self._get_full_text()
    if not text:
      messagebox.showinfo("Thông báo", "Chưa có kết quả OCR!")
      return
    self.clipboard_clear()
    self.clipboard_append(text)
    self._set_status("Đã copy vào clipboard!")


  # ── Startup toggle ─────────────────────────────────────────
  def _toggle_startup(self) -> None:
    try:
      if self._startup_var.get():
        startup_manager.enable_startup()
        method = startup_manager.get_startup_method()
        method_str = "Task Scheduler" if method == "task" else "Registry"
        self._set_status(f"✅ Đã bật khởi động cùng Windows ({method_str})")
      else:
        startup_manager.disable_startup()
        self._set_status("❌ Đã tắt khởi động cùng Windows")
      self.cfg["startup_enabled"] = self._startup_var.get()
      save_config(self.cfg)
    except Exception as e:
      messagebox.showerror("Lỗi", f"Không thể cài startup:\n{e}")

  def _on_close(self) -> None:
    self._stop_flag = True
    self.destroy()


def main() -> None:
  app = App()
  app.mainloop()


if __name__ == "__main__":
  main()
