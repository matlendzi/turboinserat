from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import os, uuid

router = APIRouter(prefix="/upload")

# Standard-Ordner für Uploads
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

@router.post("/", response_model=dict)
async def upload_file(request: Request, file: UploadFile = File(...)):
    # Ordner anlegen, falls nicht existent
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # Einzigartigen Dateinamen generieren
    ext = os.path.splitext(file.filename)[1]
    new_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, new_name)

    try:
        contents = await file.read()
        with open(dest_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload fehlgeschlagen: {e}")

    # Volle URL zum Bild zurückliefern
    full_url = str(request.base_url).rstrip("/") + f"/uploads/{new_name}"
    return {"url": full_url}
