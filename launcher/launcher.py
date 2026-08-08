import base64
import getpass
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def load_config() -> dict:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "config.json")
    if not path.exists():
        raise SystemExit(f"Config nao encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def machine_hwid() -> str:
    raw = "|".join([platform.node(), platform.platform(), str(uuid.getnode()), getpass.getuser()])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def nonce() -> str:
    return base64.urlsafe_b64encode(os.urandom(24)).decode("ascii").rstrip("=")


def verify_signature(public_key_pem: str, data: bytes, signature_b64: str) -> None:
    public_key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
    signature = base64.b64decode(signature_b64)
    public_key.verify(signature, data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def post(session: requests.Session, api_base: str, path: str, payload: dict) -> dict:
    response = session.post(f"{api_base}{path}", json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    cfg = load_config()
    api_base = cfg["api_base"].rstrip("/")
    hwid = machine_hwid()
    session = requests.Session()
    common = {
        "license_key": cfg["license_key"],
        "hwid": hwid,
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "launcher_version": cfg["launcher_version"],
    }
    register = post(session, api_base, "/api/client/register", {**common, "nonce": nonce()})
    device_id = register["device_id"]
    check = post(session, api_base, "/api/license/check", {"license_key": cfg["license_key"], "hwid": hwid, "device_id": device_id, "nonce": nonce()})
    if not check["valid"]:
        raise SystemExit("Licenca invalida")
    manifest = post(session, api_base, "/api/hunt/download", {"license_key": cfg["license_key"], "device_id": device_id, "hunt_ids": check["allowed_hunts"], "nonce": nonce()})
    work_root = Path(cfg.get("work_dir", ".launcher_work"))
    work_root.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="hunt_", dir=work_root))
    try:
        for item in manifest["hunts"]:
            response = session.get(
                f"{api_base}{item['download_url']}",
                headers={"X-License-Key": cfg["license_key"], "X-HWID": hwid, "X-Device-Id": device_id},
                timeout=60,
            )
            response.raise_for_status()
            data = response.content
            if sha256_bytes(data) != item["sha256"]:
                raise RuntimeError(f"Hash invalido para {item['name']}")
            verify_signature(manifest["public_key_pem"], data, item["signature"])
            hunt_path = run_dir / f"{item['name']}-{item['version']}.yaml"
            hunt_path.write_bytes(data)
            result_path = run_dir / f"{item['name']}-{item['version']}.result.json"
            subprocess.run([cfg["velociraptor_binary"], "--config", str(hunt_path)], check=True, stdout=result_path.open("wb"), stderr=subprocess.STDOUT)
            with result_path.open("rb") as handle:
                upload = session.post(
                    f"{api_base}/api/result/upload",
                    data={"license_key": cfg["license_key"], "hwid": hwid, "device_id": device_id, "hunt_version_id": item["version_id"]},
                    files={"file": (result_path.name, handle, "application/json")},
                    timeout=60,
                )
                upload.raise_for_status()
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
