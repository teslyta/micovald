import uuid
from fastapi import UploadFile, HTTPException

ALLOWED = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

async def save_safe_image(file: UploadFile, folder: str) -> str:
    if file.content_type not in ALLOWED:
        raise HTTPException(400, "Разрешены только изображения JPG, PNG или WEBP")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(400, "Файл превышает 5 МБ")
    fname = f"{uuid.uuid4().hex}{ALLOWED[file.content_type]}"
    with open(f"/app/media/{folder}/{fname}", "wb") as f:
        f.write(data)
    return f"/media/{folder}/{fname}"
