from pydantic import BaseModel
from typing import Optional


class Asset(BaseModel):
    id: str
    name: str
    description: str
    integration_id: str
    tenant_id: str


class Integration(BaseModel):
    id: str
    name: str
    type: str
    tenant_id: str


class HTTPError(BaseModel):
    code: int
    message: str



class CreateAssetRequest(BaseModel):
    description: str
    integration_id: str
    name: str


class UpdateAssetRequest(BaseModel):
    id: str
    description: Optional[str] = None
    name: Optional[str] = None


class CreateIntegrationRequest(BaseModel):
    name: str
    type: str


class UpdateIntegrationRequest(BaseModel):
    id: str
    name: str