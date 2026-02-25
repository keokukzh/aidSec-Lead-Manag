"""Thin HTTP client for Streamlit views to call the FastAPI backend.

All views should import from here instead of accessing the database directly.
The API_URL defaults to http://localhost:8000 and can be overridden via env var.
"""
import os
import requests
from typing import Any, Optional

API_URL = os.getenv("API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")

_HEADERS = {}
if API_KEY:
    _HEADERS["X-API-Key"] = API_KEY


class APIError(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")


def _url(path: str) -> str:
    return f"{API_URL}/api/{path.lstrip('/')}"


def _handle(r: requests.Response) -> Any:
    if r.status_code == 204:
        return None
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise APIError(r.status_code, detail)
    if "application/json" in r.headers.get("content-type", ""):
        return r.json()
    return r.content


def get(path: str, params: dict = None) -> Any:
    r = requests.get(_url(path), params=params, headers=_HEADERS, timeout=60)
    return _handle(r)


def post(path: str, json: dict = None, **kwargs) -> Any:
    r = requests.post(_url(path), json=json, headers=_HEADERS, timeout=120, **kwargs)
    return _handle(r)


def patch(path: str, json: dict = None) -> Any:
    r = requests.patch(_url(path), json=json, headers=_HEADERS, timeout=30)
    return _handle(r)


def delete(path: str) -> Any:
    r = requests.delete(_url(path), headers=_HEADERS, timeout=30)
    return _handle(r)


def put(path: str, json: dict = None) -> Any:
    r = requests.put(_url(path), json=json, headers=_HEADERS, timeout=30)
    return _handle(r)


def upload(path: str, file_bytes: bytes, filename: str, params: dict = None) -> Any:
    r = requests.post(
        _url(path),
        files={"file": (filename, file_bytes)},
        params=params,
        headers=_HEADERS,
        timeout=120,
    )
    return _handle(r)


def download(path: str, params: dict = None) -> bytes:
    r = requests.get(_url(path), params=params, headers=_HEADERS, timeout=60)
    if r.status_code >= 400:
        raise APIError(r.status_code, r.text[:200])
    return r.content


# ── Convenience wrappers ────────────────────────────────────────

def get_leads(page=1, per_page=50, status=None, kategorie=None, search=None, sort="newest"):
    params = {"page": page, "per_page": per_page, "sort": sort}
    if status:
        params["status"] = status
    if kategorie:
        params["kategorie"] = kategorie
    if search:
        params["search"] = search
    return get("leads", params)


def get_leads_pipeline(per_status=50):
    return get("leads/pipeline", {"per_status": per_status})


def get_lead(lead_id: int):
    return get(f"leads/{lead_id}")


def update_lead(lead_id: int, **fields):
    return patch(f"leads/{lead_id}", json=fields)


def delete_lead(lead_id: int):
    return delete(f"leads/{lead_id}")


def get_lead_timeline(lead_id: int):
    return get(f"leads/{lead_id}/timeline")


def create_lead(**fields):
    return post("leads", json=fields)


def bulk_status(lead_ids: list, new_status: str):
    return post("leads/bulk-status", json={"lead_ids": lead_ids, "new_status": new_status})


def get_dashboard_kpis():
    return get("dashboard/kpis")


def send_email(lead_id: int, subject: str, body: str, campaign_id: int = None):
    payload = {"lead_id": lead_id, "subject": subject, "body": body}
    if campaign_id:
        payload["campaign_id"] = campaign_id
    return post("emails/send", json=payload)


def get_email_history(lead_id: int):
    return get(f"emails/history/{lead_id}")


def generate_email(lead_id: int, email_type: str = "erstkontakt"):
    return post("emails/generate", json={"lead_id": lead_id, "email_type": email_type})


def get_templates():
    return get("emails/templates")


def get_daily_email_count():
    return get("emails/daily-count")


def smtp_test():
    return post("emails/smtp-test")


def get_global_email_history(limit=50):
    return get("emails/history", {"limit": limit})


def start_bulk_email(lead_ids: list, subject: str = "", body: str = "", delay_seconds: int = 10):
    return post("emails/bulk-send", json={
        "lead_ids": lead_ids, "subject": subject, "body": body, "delay_seconds": delay_seconds,
    })


def get_bulk_email_status(job_id: str):
    return get(f"emails/bulk-send/{job_id}")


def cancel_bulk_email(job_id: str):
    return post(f"emails/bulk-send/{job_id}/cancel")


def get_custom_templates():
    return get("emails/custom-templates")


def create_custom_template(name: str, betreff: str, inhalt: str):
    return post("emails/custom-templates", json={"name": name, "betreff": betreff, "inhalt": inhalt})


def update_custom_template(tpl_id: int, name: str, betreff: str, inhalt: str):
    return patch(f"emails/custom-templates/{tpl_id}", json={"name": name, "betreff": betreff, "inhalt": inhalt})


def delete_custom_template(tpl_id: int):
    return delete(f"emails/custom-templates/{tpl_id}")


def send_to_outlook_draft(subject: str, body: str, html_body: str = None, to_email: str = None):
    """Create an email draft in Outlook"""
    payload = {"subject": subject, "body": body}
    if html_body:
        payload["html_body"] = html_body
    if to_email:
        payload["to_email"] = to_email
    return post("emails/send-to-outlook", json=payload)


def get_outlook_configured():
    """Check if Outlook is configured"""
    return get("emails/outlook-configured")


def check_ranking(url: str):
    return post("ranking/check", json={"url": url})


def check_lead_ranking(lead_id: int):
    return post(f"ranking/check-lead/{lead_id}")


def start_batch_ranking(lead_ids: list):
    return post("ranking/batch", json={"lead_ids": lead_ids})


def get_batch_status(job_id: str):
    return get(f"ranking/batch/{job_id}")


def cancel_batch(job_id: str):
    return post(f"ranking/batch/{job_id}/cancel")


def agent_search(**kwargs):
    return post("agents/search", json=kwargs)


def agent_outreach(lead_id: int, email_type: str = "erstkontakt"):
    return post("agents/outreach", json={"lead_id": lead_id, "email_type": email_type})


def agent_research(lead_id: int):
    return post(f"agents/research/{lead_id}")


def get_llm_status():
    return get("agents/llm-status")


def get_campaigns():
    return get("campaigns")


def get_campaign(campaign_id: int):
    return get(f"campaigns/{campaign_id}")


def create_campaign(**fields):
    return post("campaigns", json=fields)


def update_campaign(campaign_id: int, **fields):
    return patch(f"campaigns/{campaign_id}", json=fields)


def delete_campaign(campaign_id: int):
    return delete(f"campaigns/{campaign_id}")


def get_campaign_leads(campaign_id: int):
    return get(f"campaigns/{campaign_id}/leads")


def assign_campaign_leads(campaign_id: int, lead_ids: list):
    return post(f"campaigns/{campaign_id}/leads", json={"lead_ids": lead_ids})


def update_campaign_lead(campaign_id: int, cl_id: int, status: str):
    return patch(f"campaigns/{campaign_id}/leads/{cl_id}", json=None)


def remove_campaign_lead(campaign_id: int, cl_id: int):
    return delete(f"campaigns/{campaign_id}/leads/{cl_id}")


def get_followups(lead_id=None, due=None):
    params = {}
    if lead_id:
        params["lead_id"] = lead_id
    if due:
        params["due"] = due
    return get("followups", params)


def create_followup(lead_id: int, datum: str, notiz: str = ""):
    return post("followups", json={"lead_id": lead_id, "datum": datum, "notiz": notiz})


def update_followup(fu_id: int, **fields):
    return patch(f"followups/{fu_id}", json=fields)


def delete_followup(fu_id: int):
    return delete(f"followups/{fu_id}")


def get_setting(key: str):
    return get(f"settings/{key}")


def put_setting(key: str, value: str):
    return put(f"settings/{key}", json={"value": value})


def get_all_settings():
    return get("settings")


def get_smtp_config():
    return get("config/smtp")


def get_llm_config():
    return get("config/llm")


def get_products():
    return get("config/products")


def get_marketing_ideas(category=None, budget=None, stage=None, search=None):
    params = {}
    if category:
        params["category"] = category
    if budget:
        params["budget"] = budget
    if stage:
        params["stage"] = stage
    if search:
        params["search"] = search
    return get("marketing/ideas", params)


def get_marketing_idea(nr: int):
    return get(f"marketing/ideas/{nr}")


def get_marketing_tracker():
    return get("marketing/tracker")


def add_to_tracker(idea_number: int, status="geplant", prioritaet=0, notizen=None):
    payload = {"idea_number": idea_number, "status": status, "prioritaet": prioritaet}
    if notizen:
        payload["notizen"] = notizen
    return post("marketing/tracker", json=payload)


def update_tracker(tracker_id: int, **fields):
    return patch(f"marketing/tracker/{tracker_id}", json=fields)


def delete_tracker(tracker_id: int):
    return delete(f"marketing/tracker/{tracker_id}")


def recommend_marketing():
    return post("marketing/recommend")


def export_csv(status=None, kategorie=None):
    params = {}
    if status:
        params["status"] = status
    if kategorie:
        params["kategorie"] = kategorie
    return download("export/csv", params)


def export_excel(status=None, kategorie=None):
    params = {}
    if status:
        params["status"] = status
    if kategorie:
        params["kategorie"] = kategorie
    return download("export/excel", params)
