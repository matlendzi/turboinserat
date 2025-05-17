from fastapi import APIRouter, HTTPException
from database import ad_collection
from schemas import IdentifyRequest
from models import StepStatus, WizardState
from datetime import datetime
from openai import OpenAI
from bson import ObjectId
from decouple import config
import json
from pydantic import BaseModel, Field
from bson.errors import InvalidId

router = APIRouter(tags=["identify"])
client = OpenAI(api_key=config("OPENAI_API_KEY"))

PROMPT_1 = """
Du bist Produkterkennungs-Experte für digitale Kleinanzeigen. 
Analysiere Nutzer-Bilder, um das Produkt zu identifizieren. 

Gib als Ergebnis ein JSON mit folgenden Feldern zurück. Die Werte in den Feldern auf deutsch!:
- brand
- model_or_type
- category
- color
- condition
- special_notes

Wähle für \"category\" exakt eine Kombination im Format \"Hauptkategorie/Unterkategorie\" aus dieser Liste:
Auto, Rad & Boot/Autos
Auto, Rad & Boot/Autoteile & Reifen
Auto, Rad & Boot/Boote & Bootszubehör
Auto, Rad & Boot/Fahrräder & Zubehör
Auto, Rad & Boot/Motorräder & Motorroller
Auto, Rad & Boot/Motorradteile & Zubehör
Auto, Rad & Boot/Nutzfahrzeuge & Anhänger
Auto, Rad & Boot/Reparaturen & Dienstleistungen
Auto, Rad & Boot/Wohnwagen & -mobile
Auto, Rad & Boot/Weiteres Auto, Rad & Boot
Elektronik/Audio & Hifi
Elektronik/Dienstleistungen Elektronik
Elektronik/Foto
Elektronik/Handy & Telefon
Elektronik/Haushaltsgeräte
Elektronik/Konsolen
Elektronik/Notebooks
Elektronik/PCs
Elektronik/PC-Zubehör & Software
Elektronik/Tablets & Reader
Elektronik/TV & Video
Elektronik/Videospiele
Elektronik/Weitere Elektronik
Haus & Garten/Badezimmer
Haus & Garten/Büro
Haus & Garten/Dekoration
Haus & Garten/Dienstleistungen Haus & Garten
Haus & Garten/Gartenzubehör & Pflanzen
Haus & Garten/Heimtextilien
Haus & Garten/Heimwerken
Haus & Garten/Küche & Esszimmer
Haus & Garten/Lampen & Licht
Haus & Garten/Schlafzimmer
Haus & Garten/Wohnzimmer
Haus & Garten/Weiteres Haus & Garten

Für \"condition\" verwende nur einen dieser Begriffe:
- Neu
- Sehr Gut
- Gut
- In Ordnung
- Defekt

\"special_notes\" kann optional Hinweise wie Zubehör oder Verpackung in deutscher Sprache enthalten.

Antworte ausschließlich mit einem gültigen JSON, keine zusätzlichen Erklärungen oder Freitexte. Werte in den Feldern auf deutsch!
"""

class IdentificationValidation(BaseModel):
    ad_process_id: str
    validated_data: dict = Field(...)

@router.post("/")
async def identify(req: IdentifyRequest):
    # Falls keine ad_process_id übergeben wurde, neues Dokument anlegen
    if not req.ad_process_id:
        new_ad = {
            "wizard_state": WizardState.STARTED,
            "identification": {
                "status": StepStatus.PENDING,
                "started_at": datetime.utcnow()
            },
            "image_urls": req.image_urls,
            "created_at": datetime.utcnow()
        }
        insert_result = await ad_collection.insert_one(new_ad)
        ad_id = insert_result.inserted_id
    else:
        # Gültige ObjectId prüfen
        try:
            ad_id = ObjectId(req.ad_process_id)
        except InvalidId:
            raise HTTPException(status_code=400, detail="Ungültige ad_process_id")

        ad = await ad_collection.find_one({"_id": ad_id})
        if not ad:
            raise HTTPException(status_code=404, detail="AdProcess not found")

        # Bei erneutem Aufruf Status und Zeit aktualisieren
        await ad_collection.update_one(
            {"_id": ad_id},
            {"$set": {
                "identification.status": StepStatus.PENDING,
                "identification.started_at": datetime.utcnow(),
                "image_urls": req.image_urls
            }}
        )

    if not req.image_urls:
        raise HTTPException(status_code=400, detail="No image URLs provided")

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT_1},
                    {"type": "input_image", "image_url": req.image_urls[0]}
                ]
            }],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[],
            temperature=1,
            max_output_tokens=2048,
            top_p=1,
            store=True
        )

        parsed_text = response.output[0].content[0].text.strip()
        # JSON-Code-Fence entfernen
        if parsed_text.startswith("```json"):
            parsed_text = parsed_text.removeprefix("```json").removesuffix("```").strip()
        elif parsed_text.startswith("```"):
            parsed_text = parsed_text.removeprefix("```").removesuffix("```").strip()

        try:
            parsed = json.loads(parsed_text)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Antwort kein gültiges JSON: {parsed_text}")

        # Ergebnis speichern
        await ad_collection.update_one(
            {"_id": ad_id},
            {"$set": {
                "identification.data": parsed,
                "identification.status": StepStatus.DONE,
                "identification.finished_at": datetime.utcnow(),
                "wizard_state": WizardState.IDENTIFIED
            }}
        )

        return {"status": "success", "ad_process_id": str(ad_id), "identification": parsed}

    except Exception as e:
        await ad_collection.update_one(
            {"_id": ad_id},
            {"$set": {"identification.status": StepStatus.ERROR}}
        )
        raise HTTPException(status_code=500, detail=f"OpenAI-Fehler: {str(e)}")


@router.patch("/validate")
async def validate_identification(data: IdentificationValidation):
    ad_id = ObjectId(data.ad_process_id)
    result = await ad_collection.update_one(
        {"_id": ad_id},
        {"$set": {
            "identification.data": data.validated_data,
            "wizard_state": WizardState.IDENTIFIED
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden oder nicht geändert")

    return {"status": "validation stored"}
