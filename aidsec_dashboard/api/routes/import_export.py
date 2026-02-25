"""Import/Export endpoints: Excel/CSV upload, data export."""
from __future__ import annotations

import io
import tempfile
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from api.dependencies import get_db, verify_api_key
from database.models import Lead, LeadStatus, LeadKategorie

router = APIRouter(tags=["import_export"], dependencies=[Depends(verify_api_key)])


@router.post("/import/excel")
def import_excel(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(400, "File must be .xlsx or .xls")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    from utils.importer import import_from_excel, import_direct
    leads_data, stats = import_from_excel(tmp_path)
    imported, duplicates = import_direct(db, leads_data)

    import os
    os.unlink(tmp_path)

    return {
        "imported": imported,
        "duplicates": duplicates,
        "total_in_file": stats.get("total", 0),
        "stats": stats,
    }


@router.post("/import/csv")
def import_csv(
    file: UploadFile = File(...),
    kategorie: str = Query("wordpress"),
    db: Session = Depends(get_db),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "File must be .csv")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    from utils.importer import import_csv as _import_csv, import_direct
    leads_data, stats = _import_csv(tmp_path, LeadKategorie(kategorie))
    imported, duplicates = import_direct(db, leads_data)

    import os
    os.unlink(tmp_path)

    return {
        "imported": imported,
        "duplicates": duplicates,
        "total_in_file": stats.get("total", 0),
    }


@router.get("/export/csv")
def export_csv(
    status: Optional[str] = None,
    kategorie: Optional[str] = None,
    db: Session = Depends(get_db),
):
    import pandas as pd
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == LeadStatus(status))
    if kategorie:
        query = query.filter(Lead.kategorie == LeadKategorie(kategorie))

    leads = query.all()
    data = []
    for l in leads:
        data.append({
            "Firma": l.firma,
            "Website": l.website or "",
            "EMail": l.email or "",
            "Telefon": l.telefon or "",
            "Stadt": l.stadt or "",
            "Kategorie": l.kategorie.value,
            "Status": l.status.value,
            "Ranking": l.ranking_score,
            "Ranking_Grade": l.ranking_grade or "",
            "Notizen": l.notes or "",
        })

    df = pd.DataFrame(data)
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")

    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"},
    )


@router.get("/export/excel")
def export_excel(
    status: Optional[str] = None,
    kategorie: Optional[str] = None,
    db: Session = Depends(get_db),
):
    import pandas as pd
    query = db.query(Lead)
    if status:
        query = query.filter(Lead.status == LeadStatus(status))
    if kategorie:
        query = query.filter(Lead.kategorie == LeadKategorie(kategorie))

    leads = query.all()
    data = []
    for l in leads:
        data.append({
            "Firma": l.firma,
            "Website": l.website or "",
            "EMail": l.email or "",
            "Telefon": l.telefon or "",
            "Stadt": l.stadt or "",
            "Kategorie": l.kategorie.value,
            "Status": l.status.value,
            "Ranking": l.ranking_score,
            "Ranking_Grade": l.ranking_grade or "",
        })

    df = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Leads")

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=leads_export.xlsx"},
    )
