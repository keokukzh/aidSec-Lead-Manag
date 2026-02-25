"""Export Utilities"""
import io
import pandas as pd
from database.models import Lead
from database.database import get_session


def _build_dataframe(filters: dict = None) -> pd.DataFrame:
    """Query leads and return as DataFrame."""
    session = get_session()
    try:
        query = session.query(Lead)

        if filters:
            if filters.get("status"):
                query = query.filter(Lead.status == filters["status"])
            if filters.get("kategorie"):
                query = query.filter(Lead.kategorie == filters["kategorie"])
            if filters.get("stadt"):
                query = query.filter(Lead.stadt.ilike(f"%{filters['stadt']}%"))

        leads = query.all()

        data = []
        for lead in leads:
            data.append({
                "Firma": lead.firma,
                "Website": lead.website or "",
                "EMail": lead.email or "",
                "Telefon": lead.telefon or "",
                "Stadt": lead.stadt or "",
                "Kategorie": lead.kategorie.value,
                "Status": lead.status.value,
                "Ranking": lead.ranking_score,
                "Ranking_Grade": lead.ranking_grade or "",
                "Notizen": lead.notes or "",
                "Erstellt": lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else ""
            })

        return pd.DataFrame(data)
    finally:
        session.close()


def export_to_csv(file_path: str = None, filters: dict = None):
    """Export leads to CSV. Returns (csv_bytes, count) if no file_path given."""
    df = _build_dataframe(filters)
    if file_path:
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        return len(df)
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    return buf.getvalue(), len(df)


def export_to_excel(file_path: str = None, filters: dict = None):
    """Export leads to Excel. Returns (excel_bytes, count) if no file_path given."""
    df = _build_dataframe(filters)
    if file_path:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Leads")
        return len(df)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Leads")
    return buf.getvalue(), len(df)
