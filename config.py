"""
config.py — App settings
"""
import json
import os
from pathlib import Path

APP_NAME = "LightOnOCR"
APP_VERSION = "1.1.0"
MODEL_ID = "onnx-community/LightOnOCR-2-1B-ONNX"

CONFIG_DIR = Path(os.getenv("APPDATA", "~")) / "LightOnOCR"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
  "output_dir": str(Path.home() / "Documents" / "OCR_Output"),
  "max_new_tokens": 4096,
  "dpi_scale": 2.77,  # 200 DPI = 72 * 2.77
  "max_longest_dim": 1540,  # HF recommended
  "theme": "dark",
  "startup_enabled": False,
  "speed_preset": "quality",  # "quality" | "fast" | "turbo"
}

SPEED_PRESETS = {
  "quality": {"max_longest_dim": 1540, "dpi_scale": 2.77, "max_new_tokens": 4096},
  "fast":    {"max_longest_dim": 1024, "dpi_scale": 2.0,  "max_new_tokens": 2048},
  "turbo":   {"max_longest_dim": 768,  "dpi_scale": 1.5,  "max_new_tokens": 1024},
}


def load_config() -> dict:
  CONFIG_DIR.mkdir(parents=True, exist_ok=True)
  if CONFIG_FILE.exists():
    try:
      with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
      return {**DEFAULTS, **data}
    except Exception:
      pass
  return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
  CONFIG_DIR.mkdir(parents=True, exist_ok=True)
  with open(CONFIG_FILE, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
