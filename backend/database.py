from motor.motor_asyncio import AsyncIOMotorClient
from decouple import config

client = AsyncIOMotorClient(config("MONGODB_URI"))
db = client["kleinanzeigen"]
ad_collection = db["ad_processes"]