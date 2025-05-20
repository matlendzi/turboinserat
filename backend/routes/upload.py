from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from PIL import Image
import os, uuid, io

router = APIRouter()

# Upload-Verzeichnis aus .env oder Default verwenden
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
BASE_URL = os.getenv("BASE_URL")

@router.post("/", response_model=dict)
async def upload_file(request: Request, file: UploadFile = File(...)):
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    ext = os.path.splitext(file.filename)[1].lower()
    new_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, new_name)

    try:
        contents = await file.read()

        if ext in [".jpg", ".jpeg", ".png"]:
            # EXIF entfernen durch Neu-Speichern des Bildes
            image = Image.open(io.BytesIO(contents))
            data = list(image.getdata())  # Bilddaten extrahieren
            clean_image = Image.new(image.mode, image.size)
            clean_image.putdata(data)

            # In Datei schreiben (überschreibt EXIF)
            clean_image.save(dest_path)
        else:
            # Nicht-Bilddateien einfach speichern
            with open(dest_path, "wb") as f:
                f.write(contents)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload fehlgeschlagen: {e}")

    base_url = BASE_URL or str(request.base_url).rstrip("/")
    if "kartenmitwirkung.de" in base_url:
        base_url = base_url.replace("http://", "https://")

    full_url = f"{base_url}/uploads/{new_name}"
    return {"url": full_url}

