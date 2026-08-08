import base64
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .audit import write_log
from .config import get_settings
from .database import Base, engine, get_db
from .deps import admin_user, current_user
from .models import Device, Hunt, HuntVersion, License, LicenseStatus, Log, Result, Session as AuthSession, User, UserRole
from .schemas import (
    AdminCreateLicenseRequest,
    AdminCreateUserRequest,
    AdminUpdateLicenseHuntsRequest,
    ClientRegisterRequest,
    ClientRegisterResponse,
    HuntDownloadRequest,
    HuntDownloadResponse,
    HuntManifestItem,
    LicenseCheckRequest,
    LicenseCheckResponse,
    LoginRequest,
    LoginResponse,
    VersionResponse,
)
from .security import create_access_token, decrypt_bytes, encrypt_bytes, hash_password, load_public_key_pem, random_license_key, sha256_file, sha256_text, sign_bytes, verify_password

settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])
app = FastAPI(title=settings.app_name)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(_: Request, exc: RateLimitExceeded):
    raise HTTPException(status_code=429, detail=str(exc))


@app.on_event("startup")
def startup() -> None:
    settings.hunt_storage_path.mkdir(parents=True, exist_ok=True)
    settings.result_storage_path.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def require_active_license(db: Session, license_key: str, hwid: str, device_id: UUID | None = None) -> tuple[License, Device | None]:
    license_obj = db.scalar(select(License).where(License.key == license_key))
    if not license_obj:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid license")
    now = datetime.now(timezone.utc)
    if license_obj.expires_at and license_obj.expires_at < now:
        license_obj.status = LicenseStatus.expired
    if license_obj.status != LicenseStatus.active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="License not active")
    hwid_hash = sha256_text(hwid)
    device = None
    if device_id:
        device = db.get(Device, device_id)
        if not device or device.license_id != license_obj.id or device.hwid_hash != hwid_hash or not device.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device not authorized")
    return license_obj, device


def reject_replay(db: Session, nonce_value: str) -> None:
    if db.scalar(select(Log.id).where(Log.payload.contains({"nonce": nonce_value})).limit(1)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Replay detected")


@app.post("/api/auth/login", response_model=LoginResponse)
@limiter.limit("10/minute")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        write_log(db, request, "login_failed", {"email": payload.email})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token, jti, expires_at = create_access_token(str(user.id), user.role.value)
    db.add(AuthSession(user_id=user.id, jti=jti, expires_at=expires_at))
    write_log(db, request, "login_success", {"email": payload.email}, user)
    db.commit()
    return LoginResponse(access_token=token, role=user.role.value)


@app.post("/api/client/register", response_model=ClientRegisterResponse)
@limiter.limit("20/minute")
def register_client(payload: ClientRegisterRequest, request: Request, db: Session = Depends(get_db)) -> ClientRegisterResponse:
    reject_replay(db, payload.nonce)
    license_obj, _ = require_active_license(db, payload.license_key, payload.hwid)
    hwid_hash = sha256_text(payload.hwid)
    device = db.scalar(select(Device).where(Device.license_id == license_obj.id, Device.hwid_hash == hwid_hash))
    if not device:
        device_count = db.scalar(select(func.count(Device.id)).where(Device.license_id == license_obj.id, Device.is_active.is_(True)))
        if device_count >= license_obj.max_devices:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Device limit reached")
        device = Device(
            license_id=license_obj.id,
            hwid_hash=hwid_hash,
            hostname=payload.hostname,
            platform=payload.platform,
            launcher_version=payload.launcher_version,
        )
        db.add(device)
    device.last_seen_at = datetime.now(timezone.utc)
    write_log(db, request, "client_registered", {"device_id": str(device.id), "nonce": payload.nonce})
    db.commit()
    return ClientRegisterResponse(device_id=device.id, license_status=license_obj.status.value, min_launcher_version=settings.launcher_min_version)


@app.post("/api/license/check", response_model=LicenseCheckResponse)
@limiter.limit("60/minute")
def check_license(payload: LicenseCheckRequest, request: Request, db: Session = Depends(get_db)) -> LicenseCheckResponse:
    reject_replay(db, payload.nonce)
    license_obj, device = require_active_license(db, payload.license_key, payload.hwid, payload.device_id)
    device.last_seen_at = datetime.now(timezone.utc)
    write_log(db, request, "license_checked", {"device_id": str(device.id), "nonce": payload.nonce})
    db.commit()
    allowed = [UUID(item) for item in license_obj.allowed_hunts.get("hunt_ids", [])]
    return LicenseCheckResponse(valid=True, status=license_obj.status.value, expires_at=license_obj.expires_at, allowed_hunts=allowed, server_time=datetime.now(timezone.utc))


@app.post("/api/hunt/download", response_model=HuntDownloadResponse)
@limiter.limit("30/minute")
def hunt_download(payload: HuntDownloadRequest, request: Request, db: Session = Depends(get_db)) -> HuntDownloadResponse:
    reject_replay(db, payload.nonce)
    license_obj = db.scalar(select(License).where(License.key == payload.license_key))
    if not license_obj:
        raise HTTPException(status_code=403, detail="Invalid license")
    allowed_ids = {UUID(item) for item in license_obj.allowed_hunts.get("hunt_ids", [])}
    if payload.hunt_ids:
        allowed_ids &= set(payload.hunt_ids)
    rows = db.scalars(
        select(HuntVersion)
        .join(Hunt, Hunt.id == HuntVersion.hunt_id)
        .where(HuntVersion.hunt_id.in_(allowed_ids), HuntVersion.is_active.is_(True), Hunt.is_active.is_(True))
    ).all()
    hunts = [
        HuntManifestItem(
            hunt_id=row.hunt_id,
            version_id=row.id,
            name=db.get(Hunt, row.hunt_id).name,
            version=row.version,
            sha256=row.sha256,
            signature=base64.b64encode(row.signature).decode("ascii"),
            download_url=f"/api/hunt/file/{row.id}",
        )
        for row in rows
    ]
    write_log(db, request, "hunt_manifest_downloaded", {"count": len(hunts), "device_id": str(payload.device_id)})
    db.commit()
    return HuntDownloadResponse(public_key_pem=load_public_key_pem(), hunts=hunts)


@app.get("/api/hunt/file/{version_id}")
def hunt_file(
    version_id: UUID,
    x_license_key: str = Header(),
    x_hwid: str = Header(),
    x_device_id: UUID = Header(),
    db: Session = Depends(get_db),
) -> Response:
    require_active_license(db, x_license_key, x_hwid, x_device_id)
    row = db.get(HuntVersion, version_id)
    if not row:
        raise HTTPException(status_code=404, detail="Hunt not found")
    return Response(content=decrypt_bytes(Path(row.file_path).read_bytes()), media_type="application/octet-stream")


@app.post("/api/result/upload")
@limiter.limit("20/minute")
def upload_result(
    request: Request,
    license_key: str,
    hwid: str,
    device_id: UUID,
    hunt_version_id: UUID | None = None,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    license_obj, device = require_active_license(db, license_key, hwid, device_id)
    target = settings.result_storage_path / str(license_obj.id) / str(device.id)
    target.mkdir(parents=True, exist_ok=True)
    output = target / file.filename
    with output.open("wb") as handle:
        handle.write(file.file.read())
    digest = sha256_file(output)
    db.add(Result(license_id=license_obj.id, device_id=device.id, hunt_version_id=hunt_version_id, file_path=str(output), sha256=digest))
    write_log(db, request, "result_uploaded", {"device_id": str(device.id), "sha256": digest})
    db.commit()
    return {"ok": True, "sha256": digest}


@app.post("/api/admin/hunts", dependencies=[Depends(admin_user)])
def upload_hunt(name: str = Form(...), version: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    hunt = db.scalar(select(Hunt).where(Hunt.name == name)) or Hunt(name=name)
    db.add(hunt)
    db.flush()
    target_dir = settings.hunt_storage_path / str(hunt.id)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{version}.yaml"
    data = file.file.read()
    digest = hashlib.sha256(data).hexdigest()
    signature = sign_bytes(data)
    target.write_bytes(encrypt_bytes(data))
    row = HuntVersion(hunt_id=hunt.id, version=version, file_path=str(target), sha256=digest, signature=signature)
    db.add(row)
    db.commit()
    return {"hunt_id": hunt.id, "version_id": row.id, "sha256": digest}


@app.get("/api/admin/dashboard", dependencies=[Depends(admin_user)])
def dashboard(db: Session = Depends(get_db)) -> dict:
    return {
        "users": db.scalar(select(func.count(User.id))),
        "licenses": db.scalar(select(func.count(License.id))),
        "devices": db.scalar(select(func.count(Device.id))),
        "hunts": db.scalar(select(func.count(Hunt.id))),
        "results": db.scalar(select(func.count(Result.id))),
        "logs": db.scalar(select(func.count()).select_from(Log)),
    }


@app.get("/api/admin/users", dependencies=[Depends(admin_user)])
def list_users(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(User).order_by(User.created_at.desc()).limit(200)).all()
    return [
        {
            "id": str(row.id),
            "email": row.email,
            "role": row.role.value,
            "status": "ativo" if row.is_active else "inativo",
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.post("/api/admin/users", dependencies=[Depends(admin_user)])
def create_user(payload: AdminCreateUserRequest, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status_code=409, detail="User already exists")
    role = UserRole.admin if payload.role == "admin" else UserRole.client
    user = User(email=payload.email, password_hash=hash_password(payload.password), role=role)
    db.add(user)
    db.commit()
    return {"id": str(user.id), "email": user.email, "role": user.role.value}


@app.get("/api/admin/licenses", dependencies=[Depends(admin_user)])
def list_licenses(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(License).order_by(License.id.desc()).limit(200)).all()
    return [
        {
            "id": str(row.id),
            "user_id": str(row.user_id),
            "key": row.key,
            "status": row.status.value,
            "max_devices": row.max_devices,
            "expires_at": row.expires_at.isoformat() if row.expires_at else "sem validade",
        }
        for row in rows
    ]


@app.post("/api/admin/licenses", dependencies=[Depends(admin_user)])
def create_license(payload: AdminCreateLicenseRequest, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    license_obj = License(
        user_id=user.id,
        key=random_license_key(),
        max_devices=payload.max_devices,
        expires_at=payload.expires_at,
        allowed_hunts={"hunt_ids": [str(item) for item in payload.allowed_hunts]},
    )
    db.add(license_obj)
    db.commit()
    return {"id": str(license_obj.id), "key": license_obj.key}


@app.post("/api/admin/licenses/{license_id}/hunts", dependencies=[Depends(admin_user)])
def update_license_hunts(license_id: UUID, payload: AdminUpdateLicenseHuntsRequest, db: Session = Depends(get_db)) -> dict:
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    license_obj.allowed_hunts = {"hunt_ids": [str(item) for item in payload.allowed_hunts]}
    db.commit()
    return {"ok": True}


@app.get("/api/admin/licenses/{license_id}/launcher", dependencies=[Depends(admin_user)])
def download_launcher_package(license_id: UUID, db: Session = Depends(get_db)) -> Response:
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    launcher_path = Path("/app/launcher/launcher.py")
    requirements_path = Path("/app/launcher/requirements.txt")
    config = {
        "api_base": settings.public_api_base,
        "license_key": license_obj.key,
        "launcher_version": settings.launcher_min_version,
        "velociraptor_binary": "velociraptor",
        "work_dir": ".launcher_work",
    }
    archive = io.BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zip_file:
        zip_file.writestr("launcher.py", launcher_path.read_text(encoding="utf-8"))
        zip_file.writestr("requirements.txt", requirements_path.read_text(encoding="utf-8"))
        zip_file.writestr("config.json", json.dumps(config, indent=2))
        zip_file.writestr("README.txt", "Execute com consentimento do jogador: python launcher.py config.json\nInstale dependencias com: pip install -r requirements.txt\n")
    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="launcher-{license_obj.key}.zip"'},
    )


@app.get("/api/admin/devices", dependencies=[Depends(admin_user)])
def list_devices(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Device).order_by(Device.last_seen_at.desc()).limit(200)).all()
    return [
        {
            "id": str(row.id),
            "license_id": str(row.license_id),
            "hostname": row.hostname,
            "platform": row.platform,
            "launcher_version": row.launcher_version,
            "status": "ativo" if row.is_active else "inativo",
            "last_seen_at": row.last_seen_at.isoformat(),
        }
        for row in rows
    ]


@app.get("/api/admin/hunts", dependencies=[Depends(admin_user)])
def list_hunts(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Hunt, HuntVersion)
        .join(HuntVersion, HuntVersion.hunt_id == Hunt.id, isouter=True)
        .order_by(Hunt.created_at.desc(), HuntVersion.created_at.desc())
        .limit(200)
    ).all()
    return [
        {
            "id": str(hunt.id),
            "name": hunt.name,
            "status": "ativo" if hunt.is_active else "inativo",
            "version": version.version if version else "-",
            "sha256": version.sha256 if version else "-",
            "created_at": hunt.created_at.isoformat(),
        }
        for hunt, version in rows
    ]


@app.get("/api/admin/results", dependencies=[Depends(admin_user)])
def list_results(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Result).order_by(Result.created_at.desc()).limit(200)).all()
    return [
        {
            "id": str(row.id),
            "license_id": str(row.license_id),
            "device_id": str(row.device_id),
            "hunt_version_id": str(row.hunt_version_id) if row.hunt_version_id else "-",
            "sha256": row.sha256,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.get("/api/admin/results/{result_id}/file", dependencies=[Depends(admin_user)])
def download_result(result_id: UUID, db: Session = Depends(get_db)) -> Response:
    result = db.get(Result, result_id)
    if not result:
        raise HTTPException(status_code=404, detail="Result not found")
    path = Path(result.file_path)
    return Response(
        content=path.read_bytes(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


@app.get("/api/admin/logs", dependencies=[Depends(admin_user)])
def list_logs(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Log).order_by(Log.created_at.desc()).limit(300)).all()
    return [
        {
            "id": str(row.id),
            "event": row.event,
            "ip_address": row.ip_address or "-",
            "payload": row.payload,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.post("/api/admin/licenses/{license_id}/expire", dependencies=[Depends(admin_user)])
def expire_license(license_id: UUID, db: Session = Depends(get_db)) -> dict:
    license_obj = db.get(License, license_id)
    if not license_obj:
        raise HTTPException(status_code=404, detail="License not found")
    license_obj.status = LicenseStatus.expired
    db.commit()
    return {"ok": True}


@app.post("/api/admin/devices/{device_id}/reset-hwid", dependencies=[Depends(admin_user)])
def reset_hwid(device_id: UUID, db: Session = Depends(get_db)) -> dict:
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    device.is_active = False
    db.commit()
    return {"ok": True}


@app.post("/api/admin/users/{user_id}/activate", dependencies=[Depends(admin_user)])
def activate_user(user_id: UUID, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    return {"ok": True}


@app.post("/api/admin/users/{user_id}/deactivate", dependencies=[Depends(admin_user)])
def deactivate_user(user_id: UUID, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    return {"ok": True}


@app.get("/api/version", response_model=VersionResponse)
def version() -> VersionResponse:
    return VersionResponse(api="1.0.0", launcher_min_version=settings.launcher_min_version)


@app.get("/api/update")
def update() -> dict:
    return {"launcher_version": settings.launcher_min_version, "rules_version": "1.0.0", "signature_version": "1.0.0"}
