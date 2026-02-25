"""Excel/CSV Import Utilities"""
import pandas as pd
from typing import List, Dict, Tuple
from database.models import Lead, LeadKategorie
from database.database import get_session


def normalize_url(url: str) -> str:
    """Normalize website URL"""
    if pd.isna(url) or not url or str(url).strip() == "":
        return ""
    url = str(url).strip().lower().rstrip('/')
    url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    return url


def normalize_email(email: str) -> str:
    """Normalize email address"""
    if pd.isna(email) or not email or str(email).strip() == "":
        return ""
    return str(email).strip().lower()


def import_from_excel(file_path: str) -> Tuple[List[Dict], Dict]:
    """
    Import leads from Excel file.
    Returns (leads_list, stats_dict)
    """
    stats = {
        "total": 0,
        "anwalt": 0,
        "praxis": 0,
        "wordpress": 0,
        "duplicates": 0,
        "errors": 0
    }

    leads = []

    # Read both sheets - note the order in the file
    try:
        # Sheet 1: Praxen Leads (350 rows)
        praxis_df = pd.read_excel(file_path, sheet_name="Praxen Leads")
        stats["praxis"] = len(praxis_df)
    except Exception as e:
        print(f"Error reading Praxen Leads sheet: {e}")
        praxis_df = pd.DataFrame()

    try:
        # Sheet 2: Anwalts Kanzleien (250 rows)
        anwalt_df = pd.read_excel(file_path, sheet_name="Anwalts Kanzleien")
        stats["anwalt"] = len(anwalt_df)
    except Exception as e:
        print(f"Error reading Anwalts Kanzleien sheet: {e}")
        anwalt_df = pd.DataFrame()

    # Process Praxen Leads (Sheet 1)
    for _, row in praxis_df.iterrows():
        try:
            firma = str(row.get("Firma", "")).strip() if pd.notna(row.get("Firma")) else ""
            if not firma:
                continue

            lead = {
                "firma": firma,
                "website": normalize_url(row.get("Website", "")),
                "email": normalize_email(row.get("EMail", "")),
                "telefon": str(row.get("Telefon", "")).strip() if pd.notna(row.get("Telefon")) else "",
                "stadt": str(row.get("Stadt", "")).strip() if pd.notna(row.get("Stadt")) else "",
                "kategorie": LeadKategorie.PRAXIS,
                "wordpress": str(row.get("WordPress", "")).lower() == "ja"
            }
            leads.append(lead)
        except Exception as e:
            stats["errors"] += 1
            print(f"Error processing praxis row: {e}")

    # Process Anwalts Kanzleien (Sheet 2)
    for _, row in anwalt_df.iterrows():
        try:
            firma = str(row.get("Firma", "")).strip() if pd.notna(row.get("Firma")) else ""
            if not firma:
                continue

            lead = {
                "firma": firma,
                "website": normalize_url(row.get("Website", "")),
                "email": normalize_email(row.get("EMail", "")),
                "telefon": str(row.get("Telefon", "")).strip() if pd.notna(row.get("Telefon")) else "",
                "stadt": str(row.get("Stadt", "")).strip() if pd.notna(row.get("Stadt")) else "",
                "kategorie": LeadKategorie.ANWALT,
                "wordpress": str(row.get("WordPress", "")).lower() == "ja"
            }
            leads.append(lead)
        except Exception as e:
            stats["errors"] += 1
            print(f"Error processing anwalt row: {e}")

    stats["total"] = len(leads)
    return leads, stats


def import_single_lead(lead_data: Dict) -> Lead:
    """Import a single lead to the database"""
    session = get_session()
    try:
        # Check for duplicates
        existing = session.query(Lead).filter(
            (Lead.email == lead_data.get("email")) |
            (Lead.website == lead_data.get("website"))
        ).first()

        if existing:
            return existing

        lead = Lead(
            firma=lead_data.get("firma", ""),
            website=lead_data.get("website", ""),
            email=lead_data.get("email", ""),
            telefon=lead_data.get("telefon", ""),
            stadt=lead_data.get("stadt", ""),
            kategorie=lead_data.get("kategorie", LeadKategorie.ANWALT),
            wordpress_detected="Ja" if lead_data.get("wordpress") else "Nein",
            quelle=lead_data.get("quelle", "manual")
        )
        session.add(lead)
        session.commit()
        return lead
    finally:
        session.close()


def import_csv(file_path: str, kategorie: LeadKategorie = LeadKategorie.WORDPRESS) -> Tuple[List[Dict], Dict]:
    """Import leads from CSV file"""
    stats = {
        "total": 0,
        "duplicates": 0,
        "errors": 0
    }

    leads = []

    try:
        df = pd.read_csv(file_path)
        for _, row in df.iterrows():
            try:
                firma = str(row.get("Firma", row.get("firma", ""))).strip() if pd.notna(row.get("Firma", row.get("firma"))) else ""
                if not firma:
                    continue

                lead = {
                    "firma": firma,
                    "website": normalize_url(row.get("Website", row.get("website", ""))),
                    "email": normalize_email(row.get("EMail", row.get("email", ""))),
                    "telefon": str(row.get("Telefon", row.get("telefon", ""))).strip() if pd.notna(row.get("Telefon", row.get("telefon"))) else "",
                    "stadt": str(row.get("Stadt", row.get("stadt", ""))).strip() if pd.notna(row.get("Stadt", row.get("stadt"))) else "",
                    "kategorie": kategorie,
                }
                leads.append(lead)
            except Exception as e:
                stats["errors"] += 1
    except Exception as e:
        stats["errors"] = 1
        print(f"CSV import error: {e}")

    stats["total"] = len(leads)
    return leads, stats


def import_direct(session, leads_data: List[Dict]) -> Tuple[int, int]:
    """Direct import with session - returns (imported, duplicates)"""
    imported = 0
    duplicates = 0

    # Pre-fetch all existing emails and websites for O(1) lookup
    existing_emails = {e for e, in session.query(Lead.email).filter(Lead.email.isnot(None)).all() if e}
    existing_websites = {w for w, in session.query(Lead.website).filter(Lead.website.isnot(None)).all() if w}

    for lead_data in leads_data:
        # Check for duplicates using pre-fetched sets
        email = lead_data.get("email")
        website = lead_data.get("website")

        if (email and email in existing_emails) or (website and website in existing_websites):
            duplicates += 1
            continue

        # Add new values to sets to detect duplicates within the import batch
        if email:
            existing_emails.add(email)
        if website:
            existing_websites.add(website)

        # Create new lead
        lead = Lead(
            firma=lead_data["firma"],
            website=lead_data["website"],
            email=lead_data["email"],
            telefon=lead_data["telefon"],
            stadt=lead_data["stadt"],
            kategorie=lead_data["kategorie"],
            wordpress_detected="Ja" if lead_data.get("wordpress") else "Nein",
            quelle="excel_import"
        )
        session.add(lead)
        imported += 1

    session.commit()
    return imported, duplicates
