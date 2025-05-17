# listing.py
from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from bson import ObjectId
from bson.json_util import dumps
from decouple import config
from database import ad_collection
from openai import OpenAI
import json

router = APIRouter()
client = OpenAI(api_key=config("OPENAI_API_KEY"))

# Hilfsfunktion für die Preisformatierung
def format_price(price: str | float | None) -> str:
    if price is None:
        return "Preis auf Anfrage"
    try:
        num_price = float(price) if isinstance(price, str) else price
        return f"{num_price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " €"
    except (ValueError, TypeError):
        return str(price)

class ListingRequest(BaseModel):
    ad_process_id: str

@router.post("/generate")
async def generate_listing(req: ListingRequest):
    ad_id = ObjectId(req.ad_process_id)
    ad = await ad_collection.find_one({"_id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="AdProcess nicht gefunden")

    features = ad.get("identification", {}).get("data", {})
    suggestion = ad.get("price_data", {}).get("suggestion", {})
    price = suggestion.get("suggested_price")

    if not features:
        raise HTTPException(status_code=400, detail="Produktmerkmale fehlen")

    preistext = format_price(price) if price is not None else "Preis auf Anfrage"

    prompt = {
        "role": "system",
        "content": """
        Du bist ein Experte für Kleinanzeigen-Texte. Deine Aufgabe:

        Erstelle aus den folgenden Produktdaten eine Anzeige mit:

        - **title** (max. 60 Zeichen):  
        Verwende klare Schlagwörter wie Produktname, Marke, Zustand und ggf. relevante Eigenschaften (sofern in den Daten enthalten).  
        Verwende keine erfundenen Begriffe. Nutze nur die bereitgestellten Informationen.

        - **description** (max. 500 Zeichen):  
        Gib möglichst viele relevante Informationen wieder: Maße, Gewicht, Kaufdatum, Zustand, Zubehör, Besonderheiten – aber **nur**, wenn sie in den Daten vorkommen.  
        Keine Halluzinationen oder Ergänzungen. Verwende ausschließlich die gelieferten Daten.  
        Du darfst freundliche Formulierungen und strukturierte Sätze nutzen, solange sie inhaltlich korrekt bleiben.  
        Wenn möglich, formuliere ehrlich und transparent, ohne Dinge hinzuzufügen, die nicht erwähnt wurden (z. B. keine Versandinfos erfinden).

        - **condition**:  
        Wird direkt aus dem übergebenen Zustand übernommen.

        - **category**:  
        Wird direkt übernommen.

        - **price**:  
        Wenn Preis vorhanden, gib ihn als Zahl aus.  
        Wenn kein Preis übergeben wird, schreibe \"Preis auf Anfrage\".

        Gib die Antwort **ausschließlich** im folgenden JSON-Format aus:

        {
        \"title\": \"...\",
        \"description\": \"...\",
        \"condition\": \"...\",
        \"category\": \"...\",
        \"price\": \"...\" // Preis auf Anfrage oder formatierter Preis
        }

        ⚠️ Wichtig: Antworte **nur basierend auf den übergebenen Daten**.  
        Erfinde keine zusätzlichen Eigenschaften, Zubehörteile oder Nutzungsangaben.
        """
    }

    user_input = {
        "role": "user",
        "content": f"Produktdaten: {json.dumps(features)}\nPreis: {preistext}"
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[prompt, user_input],
            temperature=1,
            max_tokens=2048
        )

        raw = response.choices[0].message.content.strip()
        print("🔎 GPT-Rohantwort:", raw)

        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").removesuffix("```").strip()
        elif raw.startswith("```"):
            raw = raw.removeprefix("```").removesuffix("```").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Antwort kein gültiges JSON: {raw}")
        
          # Fallbacks setzen, wenn GPT Mist baut
        parsed.setdefault("title", "Titel fehlt")
        parsed.setdefault("description", "Keine Beschreibung generiert")
        parsed.setdefault("condition", features.get("condition", "Unbekannt"))
        parsed.setdefault("category", features.get("category", "Unbekannt"))
        parsed.setdefault("price", price if price is not None else "Preis auf Anfrage")

        # Rechtliche Hinweise immer anhängen
        disclaimer = ("Der Verkauf erfolgt unter Ausschluss jeglicher Sachmängelhaftung. "
                      "Die Haftung auf Schadenersatz wegen Verletzungen von Gesundheit, Körper oder Leben "
                      "und grob fahrlässiger und/oder vorsätzlicher Verletzungen meiner Pflichten als Verkäufer bleibt davon unberührt.")
        parsed["description"] = f"{parsed['description'].rstrip()}\n\n{disclaimer}"

        await ad_collection.update_one(
            {"_id": ad_id},
            {"$set": {
                "listing": parsed,
                "wizard_state": "LISTING_READY"
            }}
        )

        return {"status": "listing generated", "title": parsed.get("title")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI-Fehler: {str(e)}")


@router.get("/ad-process/{ad_process_id}")
async def get_process_details(ad_process_id: str):
    ad_id = ObjectId(ad_process_id)
    ad = await ad_collection.find_one({"_id": ad_id}, {
        "wizard_state": 1,
        "identification.data": 1,
        "price_data.suggestion": 1,
        "listing": 1
    })
    if not ad:
        raise HTTPException(status_code=404, detail="AdProcess nicht gefunden")

    return json.loads(dumps(ad))


@router.get("/ad-processes")
async def list_ad_processes(user_id: str = Query(...)):
    results = await ad_collection.find({"user_id": user_id}).to_list(length=100)
    return json.loads(dumps(results))
