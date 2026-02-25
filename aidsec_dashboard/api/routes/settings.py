"""Settings endpoints: key-value store and config management."""
from __future__ import annotations

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from api.schemas.common import SettingOut, SettingUpdate
from database.models import Settings

router = APIRouter(tags=["settings"], dependencies=[Depends(verify_api_key)])


def _get(db: Session, key: str, default: str = "") -> str:
    row = db.query(Settings).filter(Settings.key == key).first()
    return row.value if row else default


def _set(db: Session, key: str, value: str):
    row = db.query(Settings).filter(Settings.key == key).first()
    if row:
        row.value = value
    else:
        db.add(Settings(key=key, value=value))


@router.get("/settings/{key}", response_model=SettingOut)
def get_setting(key: str, db: Session = Depends(get_db)):
    value = _get(db, key)
    return SettingOut(key=key, value=value)


@router.put("/settings/{key}", response_model=SettingOut)
def put_setting(key: str, payload: SettingUpdate, db: Session = Depends(get_db)):
    _set(db, key, payload.value)
    db.commit()
    return SettingOut(key=key, value=payload.value)


@router.get("/settings", response_model=list[SettingOut])
def list_settings(db: Session = Depends(get_db)):
    rows = db.query(Settings).order_by(Settings.key).all()
    return [SettingOut(key=r.key, value=r.value) for r in rows]


@router.put("/settings", response_model=dict)
def bulk_update_settings(payload: dict, db: Session = Depends(get_db)):
    """Bulk update multiple settings at once.

    Accepts either:
    - { "settings": { "key": "value" } }
    - { "key": "value" }
    """
    # Handle both formats
    if "settings" in payload:
        settings = payload["settings"]
    else:
        settings = payload

    updated = 0
    for key, value in settings.items():
        if value is not None:
            _set(db, key, str(value))
            updated += 1
    db.commit()
    return {"success": True, "updated": updated}


@router.get("/config/smtp")
def get_smtp_config():
    return {
        "host": os.getenv("SMTP_HOST", ""),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME", ""),
        "from_name": os.getenv("SMTP_FROM_NAME", "AidSec Team"),
        "from_email": os.getenv("SMTP_FROM_EMAIL", "noreply@aidsec.ch"),
        "configured": bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_USERNAME")),
    }


@router.get("/config/llm")
def get_llm_config():
    provider = os.getenv("DEFAULT_PROVIDER", "lm_studio")
    return {
        "provider": provider,
        "lm_studio_url": os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL", ""),
        "openai_model": os.getenv("OPENAI_MODEL", ""),
        "has_api_key": bool(os.getenv("OPENAI_API_KEY")),
    }


@router.get("/config/products")
def get_products(db: Session = Depends(get_db)):
    from services.outreach import PRODUCT_CATALOG
    custom_raw = _get(db, "products", "")
    custom = []
    if custom_raw:
        try:
            custom = json.loads(custom_raw)
        except json.JSONDecodeError:
            pass
    return {"catalog": PRODUCT_CATALOG, "custom": custom}
