from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routes.identify import router as identify_router
from routes.price import router as price_router
from routes.listing import router as listing_router
from routes.upload import router as upload_router
from config import CurrentConfig
import os

# Upload-Verzeichnis sicherstellen
UPLOAD_DIR = CurrentConfig.UPLOAD_DIR
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(debug=CurrentConfig.DEBUG)

# CORS konfigurieren, damit das Frontend Anfragen stellen kann
app.add_middleware(
    CORSMiddleware,
    allow_origins=CurrentConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API-Router einbinden
app.include_router(identify_router, prefix=f"{CurrentConfig.API_PREFIX}/identify", tags=["identify"])
app.include_router(price_router,     prefix=f"{CurrentConfig.API_PREFIX}/price",    tags=["price"])
app.include_router(listing_router,   prefix=f"{CurrentConfig.API_PREFIX}/listing",  tags=["listing"])
app.include_router(upload_router,    prefix=f"{CurrentConfig.API_PREFIX}/upload",   tags=["upload"])

# Statische Dateien ausliefern (Upload-Ordner)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

@app.get("/")
def root():
    return {"message": "Kleinanzeigen KI Wizard Backend", "environment": os.getenv("FLASK_ENV", "development")}
