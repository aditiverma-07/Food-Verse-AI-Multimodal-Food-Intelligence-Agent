"""Shared helpers: safe parsing, image/video loading."""
import base64
import io
import json
import os
import re
import tempfile

import numpy as np
from PIL import Image, ImageOps

MAX_IMAGE_MB = 10
MAX_VIDEO_MB = 50


class InputError(Exception):
    """Raised for invalid user uploads."""


def safe_float(value, default=0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            m = re.search(r"-?\d+(\.\d+)?", value.replace(",", ""))
            return float(m.group(0)) if m else default
        return float(value)
    except (TypeError, ValueError):
        return default


def extract_json(text: str):
    """Parse JSON from an LLM reply, tolerating code fences and extra prose."""
    if not text:
        raise ValueError("Empty model response.")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", cleaned, re.S)
    if m:
        return json.loads(m.group(0))
    raise ValueError("Model did not return valid JSON.")


def load_image(uploaded_file) -> Image.Image:
    """Validate and load a Streamlit UploadedFile as an RGB PIL image."""
    size_mb = uploaded_file.size / (1024 * 1024)
    if size_mb > MAX_IMAGE_MB:
        raise InputError(f"Image is {size_mb:.1f} MB; the limit is {MAX_IMAGE_MB} MB.")
    try:
        img = Image.open(io.BytesIO(uploaded_file.getvalue()))
        img.load()
        img = ImageOps.exif_transpose(img).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        raise InputError("Could not read that file as an image.") from exc
    return img


def image_to_b64(img: Image.Image, max_side: int = 1024) -> str:
    img = img.copy()
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def extract_video_frames(data: bytes, n: int = 4, suffix: str = ".mp4"):
    """Sample n evenly spaced frames from video bytes using OpenCV."""
    import cv2

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        path = tmp.name
    frames = []
    try:
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total > n:
            idxs = np.linspace(0, total - 1, n + 2)[1:-1].astype(int)
        else:
            idxs = range(max(total, 0))
        for i in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
            ok, frame = cap.read()
            if ok:
                frames.append(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        cap.release()
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    if not frames:
        raise InputError("Could not read any frames from that video.")
    return frames
