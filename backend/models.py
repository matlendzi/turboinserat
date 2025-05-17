from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class StepStatus(str, Enum):
    PENDING = "PENDING"
    DONE = "DONE"
    ERROR = "ERROR"

class WizardState(str, Enum):
    STARTED = "STARTED"
    UPLOADED = "UPLOADED"
    IDENTIFIED = "IDENTIFIED"

class IdentificationData(BaseModel):
    brand: Optional[str]
    model_or_type: Optional[str]
    main_category: Optional[str]
    sub_category: Optional[str]
    color: Optional[str]
    condition: Optional[str]
    special_notes: Optional[str]
    user_input: str

class IdentificationStep(BaseModel):
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    data: Optional[IdentificationData] = None

class AdProcess(BaseModel):
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    wizard_state: WizardState = WizardState.UPLOADED
    identification: IdentificationStep = Field(default_factory=IdentificationStep)