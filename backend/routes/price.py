# price.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from bson import ObjectId
from decouple import config
from database import ad_collection
from openai import OpenAI
from bson.errors import InvalidId
import httpx
import re
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

class AdSearchRequest(BaseModel):
    query: str
    limit: int = 5

class UpdateAttributesRequest(BaseModel):
    ad_process_id: str
    brand: str
    model_or_type: str

class ComparableRequest(BaseModel):
    ad_process_id: str

class PriceSuggestionRequest(BaseModel):
    ad_process_id: str

def extract_condition(details_text):
    if not details_text:
        return None
    match = re.search(r"Zustand:([^|]+)", details_text)
    return match.group(1).strip() if match else None

@router.post("/update_attributes")
async def update_attributes(req: UpdateAttributesRequest):
    try:
        ad_id = ObjectId(req.ad_process_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Ungültige ad_process_id")

    result = await ad_collection.update_one(
        {"_id": ad_id},
        {"$set": {
            "identification.data.brand": req.brand,
            "identification.data.model_or_type": req.model_or_type
        }}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    # modified_count kann auch 0 sein – ist ok, wenn keine Änderung

    ad = await ad_collection.find_one({"_id": ad_id})
    data = ad.get("identification", {}).get("data", {})
    return {"brand": data.get("brand"), "model_or_type": data.get("model_or_type")}


@router.post("/ads/comparables")
async def get_comparables_from_query(req: AdSearchRequest):
    api_key = config("KLEINANZEIGEN_API_KEY")
    url = "https://api.kleinanzeigen-agent.de/ads/v1/kleinanzeigen/search"

    params = {
        "query": req.query,
        "limit": str(req.limit)
    }
    headers = {
        "ads_key": api_key,
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Fehler bei Abruf der Vergleichsanzeigen: {response.text}")

    return response.json()

@router.post("/comparables")
async def fetch_and_store_comparables(req: ComparableRequest):
    ad_id = ObjectId(req.ad_process_id)
    ad = await ad_collection.find_one({"_id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="AdProcess nicht gefunden")

    data = ad.get("identification", {}).get("data", {})
    brand = data.get("brand")
    model = data.get("model_or_type")

    if not brand or not model:
        raise HTTPException(status_code=400, detail="Produktdaten unvollständig für Vergleichssuche")


    query = f"{brand} {model}"

    # Vergleichsanzeigen abrufen
    api_key = config("KLEINANZEIGEN_API_KEY")
    url = "https://api.kleinanzeigen-agent.de/ads/v1/kleinanzeigen/search"
    params = {"query": query, "limit": "5"}
    headers = {"ads_key": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Vergleichsanzeigen konnten nicht geladen werden")

    full_data = response.json()
    ads = full_data.get("data", {}).get("ads", [])

    # Nur relevante Felder extrahieren
    cleaned_ads = [
        {
            "title": ad.get("title"),
            "description": ad.get("description"),
            "price": ad.get("price"),
            "condition": extract_condition(ad.get("metadata", {}).get("details_text", ""))
        }
        for ad in ads
    ]

    await ad_collection.update_one(
        {"_id": ad_id},
        {"$set": {
            "price_data.comparables": cleaned_ads,
            "wizard_state": "COMPARABLES_RETRIEVED"
        }}
    )

    return {
        "status": "comparables saved",
        "query": query,
        "count": len(cleaned_ads)
    }

@router.post("/suggest")
async def generate_price_suggestion(req: PriceSuggestionRequest):
    ad_id = ObjectId(req.ad_process_id)
    ad = await ad_collection.find_one({"_id": ad_id})
    if not ad:
        raise HTTPException(status_code=404, detail="AdProcess nicht gefunden")

    features = ad.get("identification", {}).get("data", {})
    comparables = ad.get("price_data", {}).get("comparables", [])

    if not features or not comparables:
        raise HTTPException(status_code=400, detail="Notwendige Daten fehlen für Preisanalyse")

    prompt = {
        "role": "system",
        "content": """
            Du bist ein KI-Experte für Preisfindung gebrauchter Produkte auf Kleinanzeigenplattformen.
        Antworte **immer auf Deutsch** und gib ausschließlich gültiges JSON zurück.
        
        Du erhältst:
        (1) Produktdaten eines Nutzers
        (2) Vergleichsanzeigen ähnlicher Produkte

        Deine Aufgabe:
        - Identifiziere passende Vergleichsanzeigen zum exakt gesuchten Produkt.
        - Wenn keine passenden Anzeigen vorhanden sind, gib `"suggested_price": null`.
        - Gib immer ein Feld `"explanation"` aus:
            - Wenn Anzeigen gefunden wurden, fasse zusammen wie viele und welche Art.
            - Wenn keine passenden Anzeigen vorhanden sind, schreibe warum.

        **Wichtig:** Deine Antwort muss komplett auf Deutsch formuliert sein.
        Antworte ausschließlich mit folgendem JSON-Schema:
        {
        "suggested_price": "XX.XX",  
        "pricerelevante_faktoren": "...", 
        "explanation": "..."
        }
        """
    }

    user_input = {
        "role": "user",
        "content": f"Produktdaten: {json.dumps(features)}\nVergleichsanzeigen: {json.dumps(comparables)}"
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[prompt, user_input],
            temperature=1,
            max_tokens=1000
        )

        raw = response.choices[0].message.content.strip()

        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").removesuffix("```").strip()
        elif raw.startswith("```"):
            raw = raw.removeprefix("```").removesuffix("```").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Antwort kein gültiges JSON: {raw}")

        # Formatiere den Preis
        if "suggested_price" in parsed:
            parsed["suggested_price"] = format_price(parsed["suggested_price"])

        await ad_collection.update_one(
            {"_id": ad_id},
            {"$set": {
                "price_data.suggestion": parsed,
                "wizard_state": "PRICE_SUGGESTED"
            }}
        )

        return {
            "status": "suggestion stored",
            "suggested_price": parsed.get("suggested_price"),
            "explanation": parsed.get("explanation")
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenAI-Fehler: {str(e)}")
