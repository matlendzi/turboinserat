from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import os, uuid

router = APIRouter(prefix="/upload")

# Upload-Verzeichnis aus .env oder Default verwenden
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
BASE_URL = os.getenv("BASE_URL")  # Kann z. B. http://localhost:8000 oder https://deine-domain.de:443 sein

@router.post("/", response_model=dict)
async def upload_file(request: Request, file: UploadFile = File(...)):
    # Upload-Ordner sicherstellen
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Sicheren Dateinamen generieren
    ext = os.path.splitext(file.filename)[1]
    new_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, new_name)

    try:
        contents = await file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload fehlgeschlagen: {e}")

    # BASE_URL aus .env oder dynamisch aus Anfrage ableiten
    base_url = BASE_URL or str(request.base_url).rstrip("/")
    full_url = f"{base_url}/uploads/{new_name}"

    return {"url": full_url}
