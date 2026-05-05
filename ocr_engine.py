"""
ocr_engine.py — LightOnOCR ONNX Runtime engine (int4 quantized)
"""
import logging
import os
import time

import numpy as np
import onnxruntime as ort
from PIL import Image
from typing import Callable
from transformers import AutoConfig, AutoProcessor, GenerationConfig
from huggingface_hub import try_to_load_from_cache, snapshot_download

log = logging.getLogger("ocr_engine")

_vision_session = None
_embed_session = None
_decoder_session = None
_processor = None
_config = None
_generation_config = None
_model_id: str = ""
_is_loaded: bool = False


def get_best_device() -> str:
  try:
    if "CUDAExecutionProvider" in ort.get_available_providers():
      return "cuda"
  except Exception:
    pass
  return "cpu"


def get_device_info() -> dict:
  dev = get_best_device()
  return {"device": dev, "name": "ONNX CUDA" if dev == "cuda" else "ONNX CPU"}


def is_model_cached(model_id: str) -> bool:
  try:
    r = try_to_load_from_cache(model_id, "onnx/vision_encoder_q4.onnx")
    return r is not None and r != ""
  except Exception:
    return False


def _load_model(
  model_id: str,
  status_callback: Callable[[str], None] | None = None,
) -> None:
  global _vision_session, _embed_session, _decoder_session
  global _processor, _config, _generation_config, _model_id, _is_loaded

  if _is_loaded and _model_id == model_id:
    return

  cached = is_model_cached(model_id)
  if not cached and status_callback:
    status_callback("⬇ Đang tải model ONNX lần đầu (~600MB)…")
  elif status_callback:
    status_callback("⚙ Đang nạp model ONNX…")

  vision_model = "onnx/vision_encoder_q4.onnx"
  embed_model = "onnx/embed_tokens_q4.onnx"
  decoder_model = "onnx/decoder_model_merged_q4.onnx"

  t0 = time.time()
  folder_path = snapshot_download(
    repo_id=model_id,
    allow_patterns=[f"{vision_model}*", f"{embed_model}*", f"{decoder_model}*"],
  )

  _config = AutoConfig.from_pretrained(model_id)
  _processor = AutoProcessor.from_pretrained(model_id)
  _generation_config = GenerationConfig.from_pretrained(model_id)
  log.info("Processor loaded in %.1fs", time.time() - t0)

  if status_callback:
    status_callback("⚙ Đang nạp ONNX sessions…")

  device = get_best_device()
  providers = (
    ["CUDAExecutionProvider", "CPUExecutionProvider"]
    if device == "cuda"
    else ["CPUExecutionProvider"]
  )

  sess_opts = ort.SessionOptions()
  sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
  n_threads = os.cpu_count() or 4
  sess_opts.intra_op_num_threads = n_threads
  sess_opts.inter_op_num_threads = max(1, n_threads // 2)

  t1 = time.time()
  _vision_session = ort.InferenceSession(
    f"{folder_path}/{vision_model}", sess_opts, providers=providers
  )
  _embed_session = ort.InferenceSession(
    f"{folder_path}/{embed_model}", sess_opts, providers=providers
  )
  _decoder_session = ort.InferenceSession(
    f"{folder_path}/{decoder_model}", sess_opts, providers=providers
  )
  log.info("Sessions loaded in %.1fs | %s", time.time() - t1, providers[0])

  _model_id = model_id
  _is_loaded = True


def ocr_page(
  image: Image.Image,
  model_id: str,
  max_new_tokens: int = 4096,
  status_callback: Callable[[str], None] | None = None,
) -> str:
  """Run OCR on a single PIL image. Returns Markdown string."""
  _load_model(model_id, status_callback)
  t0 = time.time()

  inputs = _processor.apply_chat_template(
    [{"role": "user", "content": [{"type": "image", "image": image}]}],
    add_generation_prompt=True,
    tokenize=True,
    return_dict=True,
    return_tensors="pt",
  )

  input_ids = inputs["input_ids"].numpy()
  attention_mask = inputs["attention_mask"].numpy()
  has_vision = "pixel_values" in inputs
  pixel_values = inputs["pixel_values"].numpy() if has_vision else None
  batch_size = input_ids.shape[0]

  tc = _config.text_config
  num_kv_heads = tc.num_key_value_heads
  head_dim = tc.head_dim
  num_layers = tc.num_hidden_layers
  eos_token_id = _generation_config.eos_token_id
  image_token_id = _config.image_token_id

  past_cache = {}
  for i in range(num_layers):
    for kv in ("key", "value"):
      past_cache[f"past_key_values.{i}.{kv}"] = np.zeros(
        [batch_size, num_kv_heads, 0, head_dim], dtype=np.float32
      )

  generated_tokens = np.array([[]], dtype=np.int64)
  image_features = None

  for _ in range(max_new_tokens):
    inputs_embeds = _embed_session.run(None, {"input_ids": input_ids})[0]

    if has_vision and image_features is None:
      image_features = _vision_session.run(
        None, {"pixel_values": pixel_values}
      )[0]
      inputs_embeds[input_ids == image_token_id] = (
        image_features.reshape(-1, image_features.shape[-1])
      )

    logits, *present = _decoder_session.run(None, {
      "inputs_embeds": inputs_embeds,
      "attention_mask": attention_mask,
      **past_cache,
    })

    input_ids = logits[:, -1].argmax(-1, keepdims=True)
    attention_mask = np.concatenate(
      [attention_mask, np.ones((batch_size, 1), dtype=attention_mask.dtype)],
      axis=-1,
    )
    for j, key in enumerate(past_cache):
      past_cache[key] = present[j]
    generated_tokens = np.concatenate(
      [generated_tokens, input_ids], axis=-1
    )

    if np.isin(input_ids, eos_token_id).any():
      break

  result = _processor.batch_decode(
    generated_tokens, skip_special_tokens=True
  )[0]
  n_tok = generated_tokens.shape[1]
  elapsed = time.time() - t0
  log.info(
    "OCR done: %d tokens in %.1fs (%.2fs/tok) | %d chars",
    n_tok, elapsed, elapsed / max(1, n_tok), len(result),
  )
  return result


def is_model_loaded() -> bool:
  return _is_loaded


def unload_model() -> None:
  global _vision_session, _embed_session, _decoder_session
  global _processor, _config, _generation_config, _model_id, _is_loaded
  _vision_session = _embed_session = _decoder_session = None
  _processor = _config = _generation_config = None
  _model_id = ""
  _is_loaded = False
