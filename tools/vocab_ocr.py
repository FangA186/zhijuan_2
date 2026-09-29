"""Local macOS OCR invocation."""
import os
import subprocess

OCR_BIN = os.path.abspath("./tools/bin/mac_vision_ocr")

def run_ocr(image_path: str) -> str:
    """运行原生 OCR 提取页面文字"""
    if not os.path.exists(OCR_BIN):
        raise FileNotFoundError(f"OCR binary not found at {OCR_BIN}")
    if not os.path.exists(image_path):
        return ""
    try:
        proc = subprocess.run([OCR_BIN, image_path], capture_output=True, text=True, timeout=15)
        return proc.stdout or ""
    except Exception as e:
        print(f"[OCR Error] {image_path}: {e}")
        return ""


