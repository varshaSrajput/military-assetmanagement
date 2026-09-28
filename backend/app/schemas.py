from datetime import datetime
from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

class PurchaseCreate(BaseModel):
    base_id: int
    equipment_type_id: int
    quantity: int
    unit_cost: float | None = None
    purchase_date: datetime | None = None
    reference: str | None = None

class TransferCreate(BaseModel):
    asset_id: int
    to_base_id: int
    quantity: int = 1
    notes: str | None = None

class AssignmentCreate(BaseModel):
    asset_id: int
    personnel_name: str
    quantity: int = 1

class ExpenditureCreate(BaseModel):
    asset_id: int
    quantity: int = 1
    reason: str

class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
