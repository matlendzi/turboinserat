from pydantic import BaseModel
from typing import Optional

class IdentifyRequest(BaseModel):
    ad_process_id: Optional[str] = None
    image_urls: list[str]