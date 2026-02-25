"""Cached wrappers around api_client calls.

All views should import from here for data that changes infrequently.
Write operations should call the appropriate invalidate_*() function
so the next read fetches fresh data.
"""
import streamlit as st
import api_client


@st.cache_data(ttl=600)
def cached_smtp_config():
    return api_client.get_smtp_config()


@st.cache_data(ttl=600)
def cached_templates():
    return api_client.get_templates()


@st.cache_data(ttl=600)
def cached_custom_templates():
    return api_client.get_custom_templates()


@st.cache_data(ttl=600)
def cached_email_signature():
    try:
        return api_client.get_setting("email_signature").get("value", "")
    except Exception:
        return ""


@st.cache_data(ttl=120)
def cached_dashboard_kpis():
    return api_client.get_dashboard_kpis()


@st.cache_data(ttl=30)
def cached_llm_status():
    return api_client.get_llm_status()


@st.cache_data(ttl=120)
def cached_marketing_tracker():
    return api_client.get_marketing_tracker()


@st.cache_data(ttl=60)
def cached_daily_email_count():
    return api_client.get_daily_email_count()


@st.cache_data(ttl=600)
def cached_all_settings():
    return api_client.get_all_settings()


@st.cache_data(ttl=300)
def cached_campaigns():
    return api_client.get("campaigns")


@st.cache_data(ttl=300)
def cached_lead_counts():
    return api_client.get("dashboard/lead-counts")


def invalidate_leads():
    """Call after lead create/update/delete."""
    cached_dashboard_kpis.clear()
    cached_lead_counts.clear()


def invalidate_email():
    """Call after SMTP config change."""
    cached_smtp_config.clear()
    cached_daily_email_count.clear()


def invalidate_templates():
    """Call after template create/update/delete."""
    cached_templates.clear()
    cached_custom_templates.clear()


def invalidate_settings():
    """Call after any setting change."""
    cached_all_settings.clear()
    cached_email_signature.clear()
    cached_smtp_config.clear()


def invalidate_marketing():
    """Call after marketing tracker changes."""
    cached_marketing_tracker.clear()


def invalidate_campaigns():
    """Call after campaign changes."""
    cached_campaigns.clear()
    cached_lead_counts.clear()
