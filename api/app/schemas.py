from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ClientRegisterRequest(BaseModel):
    license_key: str
    hwid: str
    hostname: str
    platform: str
    launcher_version: str
    nonce: str


class ClientRegisterResponse(BaseModel):
    device_id: UUID
    license_status: str
    min_launcher_version: str


class LicenseCheckRequest(BaseModel):
    license_key: str
    hwid: str
    device_id: UUID
    nonce: str


class LicenseCheckResponse(BaseModel):
    valid: bool
    status: str
    expires_at: datetime | None
    allowed_hunts: list[UUID]
    server_time: datetime


class HuntDownloadRequest(BaseModel):
    license_key: str
    device_id: UUID
    hunt_ids: list[UUID] | None = None
    nonce: str


class HuntManifestItem(BaseModel):
    hunt_id: UUID
    version_id: UUID
    name: str
    version: str
    sha256: str
    signature: str
    download_url: str


class HuntDownloadResponse(BaseModel):
    public_key_pem: str
    hunts: list[HuntManifestItem]


class VersionResponse(BaseModel):
    api: str
    launcher_min_version: str


class AdminCreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: str = "client"


class AdminCreateLicenseRequest(BaseModel):
    user_id: UUID
    max_devices: int = Field(default=1, ge=1, le=20)
    expires_at: datetime | None = None
    allowed_hunts: list[UUID] = Field(default_factory=list)


class AdminUpdateLicenseHuntsRequest(BaseModel):
    allowed_hunts: list[UUID]
