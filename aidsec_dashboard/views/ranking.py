"""Ranking Page - Security Headers Check — powered by API"""
import streamlit as st
import pandas as pd
import time
import api_client
from cache_helpers import cached_dashboard_kpis

GRADE_HTML = {
    "A": '<span class="grade-badge grade-A">A</span>',
    "B": '<span class="grade-badge grade-B">B</span>',
    "C": '<span class="grade-badge grade-C">C</span>',
    "D": '<span class="grade-badge grade-D">D</span>',
    "F": '<span class="grade-badge grade-F">F</span>',
}


def render():
    st.title("🔍 Security Headers Ranking")

    flash = st.session_state.pop("ranking_flash", None)
    if flash:
        if flash["type"] == "success":
            grade = flash["grade"]
            badge = GRADE_HTML.get(grade, grade)
            st.markdown(
                f'<div style="background:#1a3a2a;border:1px solid #2ecc71;border-radius:8px;'
                f'padding:12px 16px;margin-bottom:16px;display:flex;align-items:center;gap:12px;">'
                f'<span style="font-size:1.3rem;">✅</span>'
                f'<span style="color:#e8eaed;font-weight:600;">{flash["firma"]}</span>'
                f'<span style="color:#b8bec6;">—</span>'
                f'{badge}'
                f'<span style="color:#b8bec6;font-family:JetBrains Mono,monospace;">'
                f'{flash["score"]}/100 Punkte</span>'
                f'<span style="color:#2ecc71;margin-left:auto;font-size:0.85rem;">'
                f'Gespeichert ✓</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.error(f"❌ Fehler bei {flash.get('firma', '?')}: {flash.get('error', 'Unbekannt')}")

    try:
        all_result = api_client.get_leads(page=1, per_page=1)
        total_leads = all_result.get("total", 0)
    except Exception as e:
        st.error(f"API nicht erreichbar: {e}")
        return

    if total_leads == 0:
        st.warning("Keine Leads vorhanden. Bitte importieren Sie zuerst Leads.")
        return

    try:
        kpis = cached_dashboard_kpis()
        grade_dist = kpis.get("grades", {})
    except Exception:
        grade_dist = {}

    checked_count = sum(grade_dist.values())
    unchecked_count = total_leads - checked_count
    avg_score = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Leads", total_leads)
    col2.metric("Geprüft", checked_count)
    col3.metric("Ungeprüft", unchecked_count)
    col4.metric("Verteilung", f"{checked_count} geprüft")

    st.markdown("---")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("🔍 Ranking prüfen")

        filter_kategorie = st.selectbox("Kategorie", ["Alle", "anwalt", "praxis", "wordpress"])

        try:
            result = api_client.get_leads(
                page=1, per_page=200,
                kategorie=filter_kategorie if filter_kategorie != "Alle" else None,
                sort="newest",
            )
            all_leads = result.get("items", [])
        except Exception:
            all_leads = []

        leads_with_website = [l for l in all_leads if l.get("website")]
        only_unchecked = st.checkbox("Nur ungeprüfte", value=True)
        if only_unchecked:
            leads_to_check = [l for l in leads_with_website if not l.get("ranking_score")]
        else:
            leads_to_check = leads_with_website

        st.write(f"**{len(leads_to_check)}** Leads zum Prüfen")

        delay = st.slider("Verzögerung zwischen Requests (Sek.)", 0.1, 3.0, 0.5, 0.1)

    with col2:
        st.write("")
        st.write("")
        if st.button("📊 Alle prüfen (Batch)", type="primary"):
            st.session_state["batch_cancel"] = False
            run_batch_check(leads_to_check, delay)

    st.markdown("---")
    st.subheader("🎯 Einzelne Website")

    leads_without = [l for l in leads_with_website if not l.get("ranking_score")]
    options = leads_without[:100] if leads_without else leads_with_website[:100]

    if options:
        selected_id = st.selectbox(
            "Lead auswählen",
            range(len(options)),
            format_func=lambda i: f"{options[i]['firma']} - {options[i].get('website', '?')}",
        )

        if st.button("🚀 Jetzt prüfen", type="primary"):
            lead = options[selected_id]
            check_single(lead["id"], lead.get("firma", "?"), lead.get("website", ""))

    st.markdown("---")
    st.subheader("📋 Ergebnisse")

    if checked_count > 0:
        st.markdown(
            '<div style="display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px;">'
            + "".join(
                f'<div style="text-align:center;">'
                f'{GRADE_HTML.get(g, g)}'
                f'<div style="font-family:JetBrains Mono,monospace;font-size:1.1rem;font-weight:600;margin-top:4px;color:#e8eaed;">'
                f'{grade_dist.get(g, 0)}</div></div>'
                for g in ["A", "B", "C", "D", "F"]
            )
            + '</div>',
            unsafe_allow_html=True,
        )

        st.markdown("---")

        try:
            result = api_client.get_leads(page=1, per_page=50, sort="ranking_desc")
            ranked_items = [i for i in result.get("items", []) if i.get("ranking_score")]
        except Exception:
            ranked_items = []

        if ranked_items:
            data = []
            for lead in ranked_items:
                grade = lead.get("ranking_grade") or "-"
                data.append({
                    "Firma": lead["firma"],
                    "Website": (lead.get("website", "")[:35] + "...") if lead.get("website") and len(lead["website"]) > 35 else (lead.get("website") or "-"),
                    "Kategorie": lead.get("kategorie", "-"),
                    "Grade": grade,
                    "Score": lead.get("ranking_score") or "-",
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Noch keine Rankings geprüft.")


def check_single(lead_id: int, firma: str, website: str):
    with st.spinner(f"Prüfe {website}..."):
        try:
            result = api_client.check_lead_ranking(lead_id)
            if result.get("grade"):
                st.session_state["ranking_flash"] = {
                    "type": "success",
                    "firma": firma,
                    "grade": result["grade"],
                    "score": result.get("score", 0),
                }
            else:
                st.session_state["ranking_flash"] = {
                    "type": "error",
                    "firma": firma,
                    "error": result.get("error", "Unbekannt"),
                }
        except Exception as e:
            st.session_state["ranking_flash"] = {
                "type": "error",
                "firma": firma,
                "error": str(e),
            }
        st.rerun()


def run_batch_check(leads, delay: float = 0.5):
    """Start batch ranking as a background task and poll for progress."""
    if not leads:
        st.warning("Keine Leads zum Prüfen!")
        return

    lead_ids = [l["id"] for l in leads]
    total = len(lead_ids)

    try:
        resp = api_client.start_batch_ranking(lead_ids)
        job_id = resp.get("job_id")
        if not job_id:
            st.error("Batch-Job konnte nicht gestartet werden.")
            return
    except Exception as e:
        st.error(f"Fehler beim Starten: {e}")
        return

    progress_bar = st.progress(0)
    status_text = st.empty()
    cancel_placeholder = st.empty()

    while True:
        if cancel_placeholder.button("Abbrechen", key=f"cancel_batch_{job_id}"):
            try:
                api_client.cancel_batch(job_id)
            except Exception:
                pass
            status_text.text("Abgebrochen!")
            break

        try:
            job = api_client.get_batch_status(job_id)
        except Exception:
            time.sleep(2)
            continue

        completed = job.get("completed", 0)
        errors = job.get("errors", 0)
        job_total = job.get("total", total)
        job_status = job.get("status", "running")

        progress_bar.progress(min(1.0, completed / max(1, job_total)))
        status_text.text(
            f"Fortschritt: {completed}/{job_total} geprüft "
            f"({errors} Fehler) ..."
        )

        if job_status in ("done", "error"):
            break

        time.sleep(2)

    cancel_placeholder.empty()

    job = api_client.get_batch_status(job_id)
    completed = job.get("completed", 0)
    errors = job.get("errors", 0)
    successful = completed - errors

    progress_bar.progress(1.0)
    status_text.text("Fertig!")
    st.success(f"Batch Check: {successful}/{total} erfolgreich, {errors} Fehler.")

    if job.get("status") == "error":
        st.error(f"Job-Fehler: {job.get('error', 'Unbekannt')}")
