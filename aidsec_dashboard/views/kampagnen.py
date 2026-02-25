"""Kampagnen Page - Campaign Management, Sequences & Analytics — partially API-driven.

Note: Campaign sending still uses direct DB access for progress-bar support and
transactional integrity during the send loop. Read operations use the API.
"""
import streamlit as st
import time
from datetime import datetime, timedelta
from database.database import get_session
from database.models import (
    Lead, LeadStatus, LeadKategorie, EmailHistory, EmailStatus,
    StatusHistory, Campaign, CampaignStatus, CampaignLead,
)
from services.email_service import get_email_service, DEFAULT_TEMPLATES
from services.outreach import (
    get_recommended_product,
    EMAIL_TYPE_LABELS,
    EMAIL_TYPE_COLORS,
)
import api_client
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from sqlalchemy import func

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#e8eaed"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
    yaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
)
PLOTLY_CONFIG = {"displayModeBar": False}

STATUS_BADGE = {
    CampaignStatus.ENTWURF: ("Entwurf", "#b8bec6", "#b8bec635"),
    CampaignStatus.AKTIV: ("Aktiv", "#2ecc71", "#2ecc7135"),
    CampaignStatus.PAUSIERT: ("Pausiert", "#f39c12", "#f39c1235"),
    CampaignStatus.ABGESCHLOSSEN: ("Abgeschlossen", "#7f8c8d", "#7f8c8d35"),
}

DEFAULT_SEQUENZ = [
    {"typ": "erstkontakt", "delay_tage": 0, "template_id": None},
    {"typ": "nachfassen", "delay_tage": 3, "template_id": None},
    {"typ": "angebot", "delay_tage": 7, "template_id": None},
]

KATEGORIE_LABELS = {
    None: "Alle Kategorien",
    LeadKategorie.PRAXIS: "Praxen",
    LeadKategorie.ANWALT: "Kanzleien",
    LeadKategorie.WORDPRESS: "WordPress",
}


def render():
    st.title("🎯 Kampagnen")

    tab_overview, tab_create, tab_detail, tab_analytics = st.tabs([
        "Übersicht", "Neue Kampagne", "Kampagnen-Detail", "Analytik",
    ])

    with tab_overview:
        _render_overview()
    with tab_create:
        _render_create()
    with tab_detail:
        _render_detail()
    with tab_analytics:
        _render_analytics()


def _render_overview():
    session = get_session()
    try:
        campaigns = session.query(Campaign).order_by(Campaign.created_at.desc()).all()
        aktiv = sum(1 for c in campaigns if c.status == CampaignStatus.AKTIV)
        total_leads_in_campaigns = session.query(CampaignLead).count()
        due_today = session.query(CampaignLead).filter(
            CampaignLead.cl_status == "aktiv",
            CampaignLead.next_send_at <= datetime.utcnow(),
        ).count()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Kampagnen gesamt", len(campaigns))
        c2.metric("Aktive", aktiv)
        c3.metric("Leads in Kampagnen", total_leads_in_campaigns)
        c4.metric("Fällige Emails", due_today)

        st.markdown("---")

        if not campaigns:
            st.info("Noch keine Kampagnen erstellt. Erstelle deine erste Kampagne im Tab 'Neue Kampagne'.")
            return

        for camp in campaigns:
            badge_label, badge_color, badge_bg = STATUS_BADGE.get(
                camp.status, ("?", "#b8bec6", "#b8bec635")
            )
            n_leads = len(camp.campaign_leads)
            completed = sum(1 for cl in camp.campaign_leads if cl.cl_status == "abgeschlossen")
            progress = completed / max(1, n_leads)

            with st.container(border=True):
                h1, h2, h3 = st.columns([3, 1, 1])
                with h1:
                    st.markdown(
                        f"**{camp.name}** "
                        f'<span style="background:{badge_bg};color:{badge_color};'
                        f'padding:2px 10px;border-radius:12px;font-size:0.8rem;'
                        f'font-weight:600;border:1px solid {badge_color}44;'
                        f'font-family:JetBrains Mono,monospace;">{badge_label}</span>',
                        unsafe_allow_html=True,
                    )
                    if camp.beschreibung:
                        st.caption(camp.beschreibung[:100])
                with h2:
                    st.metric("Leads", n_leads)
                with h3:
                    kat_label = KATEGORIE_LABELS.get(camp.kategorie_filter, "Alle")
                    st.metric("Kategorie", kat_label)

                st.progress(progress, text=f"{completed}/{n_leads} abgeschlossen")

                bc1, bc2, bc3, bc4 = st.columns(4)
                with bc1:
                    if camp.status == CampaignStatus.ENTWURF:
                        if st.button("▶ Starten", key=f"start_{camp.id}"):
                            camp.status = CampaignStatus.AKTIV
                            camp.start_datum = datetime.utcnow()
                            _init_next_send(session, camp)
                            session.commit()
                            st.rerun()
                    elif camp.status == CampaignStatus.AKTIV:
                        if st.button("⏸ Pausieren", key=f"pause_{camp.id}"):
                            camp.status = CampaignStatus.PAUSIERT
                            session.commit()
                            st.rerun()
                    elif camp.status == CampaignStatus.PAUSIERT:
                        if st.button("▶ Fortsetzen", key=f"resume_{camp.id}"):
                            camp.status = CampaignStatus.AKTIV
                            session.commit()
                            st.rerun()
                with bc2:
                    if camp.status == CampaignStatus.AKTIV:
                        due = sum(
                            1 for cl in camp.campaign_leads
                            if cl.cl_status == "aktiv" and cl.next_send_at and cl.next_send_at <= datetime.utcnow()
                        )
                        if due > 0 and st.button(f"📤 {due} fällige senden", key=f"send_{camp.id}"):
                            st.session_state["kampagne_send_id"] = camp.id
                            st.rerun()
                with bc3:
                    if st.button("📊 Detail", key=f"detail_{camp.id}"):
                        st.session_state["kampagne_detail_id"] = camp.id
                        st.rerun()
                with bc4:
                    if camp.status in (CampaignStatus.ENTWURF, CampaignStatus.PAUSIERT, CampaignStatus.ABGESCHLOSSEN):
                        if st.button("🗑 Löschen", key=f"del_{camp.id}"):
                            session.delete(camp)
                            session.commit()
                            st.rerun()
    finally:
        session.close()


def _init_next_send(session, campaign: Campaign):
    seq = campaign.sequenz or DEFAULT_SEQUENZ
    if not seq:
        return
    first_delay = seq[0].get("delay_tage", 0)
    target = datetime.utcnow() + timedelta(days=first_delay)
    for cl in campaign.campaign_leads:
        if cl.cl_status == "aktiv" and cl.current_step == 0 and not cl.next_send_at:
            cl.next_send_at = target
    session.flush()


def _render_create():
    session = get_session()
    try:
        st.subheader("Neue Kampagne erstellen")

        with st.form("create_campaign_form"):
            name = st.text_input("Kampagnen-Name", placeholder="z.B. 2026-Q1-Praxen-Security")
            beschreibung = st.text_area("Beschreibung", placeholder="Ziel und Kontext der Kampagne...")

            kat_options = list(KATEGORIE_LABELS.keys())
            kat_labels = list(KATEGORIE_LABELS.values())
            kat_idx = st.selectbox("Zielgruppe (Kategorie-Filter)", kat_labels, index=0)
            kat_val = kat_options[kat_labels.index(kat_idx)]

            st.markdown("##### Sequenz-Schritte")
            s1_typ = st.selectbox("Schritt 1 — Typ", list(EMAIL_TYPE_LABELS.values()), index=0, key="s1_typ")
            s1_delay = st.number_input("Schritt 1 — Verzögerung (Tage)", value=0, min_value=0, key="s1_delay")

            s2_typ = st.selectbox("Schritt 2 — Typ", list(EMAIL_TYPE_LABELS.values()), index=1, key="s2_typ")
            s2_delay = st.number_input("Schritt 2 — Verzögerung (Tage)", value=3, min_value=0, key="s2_delay")

            s3_typ = st.selectbox("Schritt 3 — Typ", list(EMAIL_TYPE_LABELS.values()), index=2, key="s3_typ")
            s3_delay = st.number_input("Schritt 3 — Verzögerung (Tage)", value=7, min_value=0, key="s3_delay")

            submitted = st.form_submit_button("Kampagne erstellen", type="primary")

        if submitted and name.strip():
            typ_reverse = {v: k for k, v in EMAIL_TYPE_LABELS.items()}
            sequenz = [
                {"typ": typ_reverse.get(s1_typ, "erstkontakt"), "delay_tage": s1_delay, "template_id": None},
                {"typ": typ_reverse.get(s2_typ, "nachfassen"), "delay_tage": s2_delay, "template_id": None},
                {"typ": typ_reverse.get(s3_typ, "angebot"), "delay_tage": s3_delay, "template_id": None},
            ]
            new_camp = Campaign(
                name=name.strip(),
                beschreibung=beschreibung.strip() if beschreibung else None,
                kategorie_filter=kat_val,
                sequenz=sequenz,
                status=CampaignStatus.ENTWURF,
            )
            session.add(new_camp)
            session.flush()
            st.session_state["new_campaign_id"] = new_camp.id
            session.commit()
            st.success(f"Kampagne '{name}' erstellt! Füge jetzt Leads hinzu.")
            st.rerun()

        new_id = st.session_state.get("new_campaign_id")
        if new_id:
            _render_lead_assignment(session, new_id)
    finally:
        session.close()


def _render_lead_assignment(session, campaign_id: int):
    camp = session.query(Campaign).get(campaign_id)
    if not camp:
        st.warning("Kampagne nicht gefunden.")
        return

    st.markdown("---")
    st.subheader(f"Leads zuweisen — {camp.name}")

    already_ids = {cl.lead_id for cl in camp.campaign_leads}

    lead_query = session.query(Lead).filter(
        Lead.status == LeadStatus.OFFEN,
        Lead.email.isnot(None),
        Lead.email != "",
    )
    if camp.kategorie_filter is not None:
        lead_query = lead_query.filter(Lead.kategorie == camp.kategorie_filter)
    available = lead_query.order_by(Lead.firma).all()
    available = [l for l in available if l.id not in already_ids]

    if not available:
        st.info("Keine passenden offenen Leads mit E-Mail-Adresse verfügbar.")
        return

    search = st.text_input("Leads suchen...", key="camp_lead_search", placeholder="Firma, Stadt...")
    if search:
        s = search.lower()
        available = [l for l in available if s in (l.firma or "").lower() or s in (l.stadt or "").lower()]

    st.caption(f"{len(available)} Leads verfügbar")

    select_all = st.checkbox("Alle auswählen", key="camp_select_all")

    selected_ids = []
    for lead in available[:100]:
        checked = st.checkbox(
            f"{lead.firma} — {lead.stadt or '?'} ({lead.kategorie.value})",
            value=select_all,
            key=f"camp_lead_{lead.id}",
        )
        if checked:
            selected_ids.append(lead.id)

    if len(available) > 100:
        st.caption(f"... und {len(available) - 100} weitere. Nutze die Suche um zu filtern.")

    if st.button(f"✅ {len(selected_ids)} Leads hinzufügen", type="primary", disabled=len(selected_ids) == 0):
        for lid in selected_ids:
            cl = CampaignLead(
                campaign_id=campaign_id,
                lead_id=lid,
                current_step=0,
                cl_status="aktiv",
            )
            session.add(cl)
        session.commit()
        st.success(f"{len(selected_ids)} Leads zur Kampagne hinzugefügt!")
        del st.session_state["new_campaign_id"]
        st.rerun()


def _render_detail():
    session = get_session()
    try:
        campaigns = session.query(Campaign).order_by(Campaign.created_at.desc()).all()
        if not campaigns:
            st.info("Keine Kampagnen vorhanden.")
            return

        preselect = st.session_state.get("kampagne_detail_id")
        camp_map = {c.id: c for c in campaigns}
        camp_names = [f"{c.name} ({STATUS_BADGE.get(c.status, ('?',))[0]})" for c in campaigns]
        default_idx = 0
        if preselect and preselect in camp_map:
            default_idx = [c.id for c in campaigns].index(preselect)

        sel_idx = st.selectbox("Kampagne auswählen", range(len(campaigns)),
                               format_func=lambda i: camp_names[i],
                               index=default_idx, key="detail_sel")
        camp = campaigns[sel_idx]

        badge_label, badge_color, badge_bg = STATUS_BADGE.get(camp.status, ("?", "#b8bec6", "#b8bec635"))
        st.markdown(
            f'### {camp.name} '
            f'<span style="background:{badge_bg};color:{badge_color};'
            f'padding:2px 10px;border-radius:12px;font-size:0.8rem;'
            f'font-weight:600;border:1px solid {badge_color}44;'
            f'font-family:JetBrains Mono,monospace;">{badge_label}</span>',
            unsafe_allow_html=True,
        )
        if camp.beschreibung:
            st.caption(camp.beschreibung)

        cls = camp.campaign_leads
        n_total = len(cls)
        n_aktiv = sum(1 for cl in cls if cl.cl_status == "aktiv")
        n_done = sum(1 for cl in cls if cl.cl_status == "abgeschlossen")
        n_paused = sum(1 for cl in cls if cl.cl_status == "pausiert")

        seq = camp.sequenz or DEFAULT_SEQUENZ
        step_dist = {}
        for cl in cls:
            step_dist[cl.current_step] = step_dist.get(cl.current_step, 0) + 1

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Leads gesamt", n_total)
        mc2.metric("Aktiv", n_aktiv)
        mc3.metric("Abgeschlossen", n_done)
        mc4.metric("Pausiert", n_paused)

        st.markdown("---")

        st.markdown("##### Sequenz-Fortschritt")
        scols = st.columns(len(seq))
        for i, step in enumerate(seq):
            with scols[i]:
                et = step.get("typ", "?")
                label = EMAIL_TYPE_LABELS.get(et, et)
                color = EMAIL_TYPE_COLORS.get(et, "#b8bec6")
                count_at = step_dist.get(i, 0)
                delay = step.get("delay_tage", 0)
                st.markdown(
                    f'<div style="text-align:center;padding:8px;border:1px solid {color}44;'
                    f'border-radius:8px;background:{color}11;">'
                    f'<div style="font-weight:700;color:{color};font-size:0.9rem;">'
                    f'Schritt {i+1}</div>'
                    f'<div style="font-size:0.8rem;color:#e8eaed;">{label}</div>'
                    f'<div style="font-family:JetBrains Mono;font-size:1.2rem;'
                    f'font-weight:700;color:{color};margin:4px 0;">{count_at}</div>'
                    f'<div style="font-size:0.78rem;color:#b8bec6;">Tag +{delay}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("---")

        if camp.status == CampaignStatus.AKTIV or st.session_state.get("kampagne_send_id") == camp.id:
            _render_send_due(session, camp)

        st.markdown("##### Leads in Kampagne")
        if not cls:
            st.info("Keine Leads zugewiesen.")
            _render_add_more_leads(session, camp)
            return

        for cl in sorted(cls, key=lambda x: (x.cl_status != "aktiv", x.current_step)):
            lead = cl.lead
            if not lead:
                continue
            step_info = seq[cl.current_step] if cl.current_step < len(seq) else None
            step_label = EMAIL_TYPE_LABELS.get(step_info["typ"], "?") if step_info else "Fertig"
            next_str = cl.next_send_at.strftime("%d.%m.%Y %H:%M") if cl.next_send_at else "-"

            cl_color = "#2ecc71" if cl.cl_status == "aktiv" else "#f39c12" if cl.cl_status == "pausiert" else "#b8bec6"

            with st.container(border=True):
                lc1, lc2, lc3, lc4 = st.columns([3, 1, 1, 1])
                with lc1:
                    st.markdown(f"**{lead.firma}** — {lead.stadt or '?'}")
                    st.caption(f"{lead.email or 'Keine E-Mail'}")
                with lc2:
                    st.markdown(
                        f'<span style="color:{cl_color};font-weight:600;'
                        f'font-size:0.8rem;">{cl.cl_status.title()}</span>',
                        unsafe_allow_html=True,
                    )
                with lc3:
                    st.markdown(f"Schritt {cl.current_step + 1}/{len(seq)}: **{step_label}**")
                with lc4:
                    st.caption(f"Nächste: {next_str}")

                ac1, ac2 = st.columns(2)
                with ac1:
                    if cl.cl_status == "aktiv":
                        if st.button("⏸", key=f"cl_pause_{cl.id}", help="Pausieren"):
                            cl.cl_status = "pausiert"
                            session.commit()
                            st.rerun()
                    elif cl.cl_status == "pausiert":
                        if st.button("▶", key=f"cl_resume_{cl.id}", help="Fortsetzen"):
                            cl.cl_status = "aktiv"
                            session.commit()
                            st.rerun()
                with ac2:
                    if st.button("🗑", key=f"cl_del_{cl.id}", help="Entfernen"):
                        session.delete(cl)
                        session.commit()
                        st.rerun()

        _render_add_more_leads(session, camp)
    finally:
        session.close()


def _render_add_more_leads(session, camp: Campaign):
    with st.expander("Weitere Leads hinzufuegen"):
        _render_lead_assignment(session, camp.id)


def _render_send_due(session, campaign: Campaign):
    seq = campaign.sequenz or DEFAULT_SEQUENZ
    now = datetime.utcnow()

    due_cls = [
        cl for cl in campaign.campaign_leads
        if cl.cl_status == "aktiv"
        and cl.next_send_at is not None
        and cl.next_send_at <= now
        and cl.current_step < len(seq)
    ]

    if not due_cls:
        st.info("Keine fälligen E-Mails.")
        if "kampagne_send_id" in st.session_state:
            del st.session_state["kampagne_send_id"]
        return

    st.markdown(f"##### 📤 {len(due_cls)} fällige E-Mails")

    email_svc = get_email_service()
    if not email_svc.is_configured():
        st.error("SMTP ist nicht konfiguriert.")
        return

    try:
        sig_text = api_client.get_setting("email_signature").get("value", "")
    except Exception:
        sig_text = ""

    preview_data = []
    for cl in due_cls:
        lead = cl.lead
        step = seq[cl.current_step]
        preview_data.append({
            "Firma": lead.firma,
            "E-Mail": lead.email or "-",
            "Schritt": f"{cl.current_step + 1}: {EMAIL_TYPE_LABELS.get(step['typ'], '?')}",
        })

    df = pd.DataFrame(preview_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    delay = st.slider("Verzögerung zwischen E-Mails (Sekunden)", 5, 60, 10, key="camp_send_delay")

    if st.button(f"📤 Alle {len(due_cls)} E-Mails jetzt senden", type="primary", key="camp_send_all"):
        progress = st.progress(0)
        status_text = st.empty()
        sent = 0
        errors = 0

        for i, cl in enumerate(due_cls):
            lead = cl.lead
            if not lead or not lead.email:
                errors += 1
                continue

            step = seq[cl.current_step]
            email_type = step.get("typ", "erstkontakt")
            product = get_recommended_product(lead.kategorie.value if lead.kategorie else "praxis")

            tpl = DEFAULT_TEMPLATES.get(email_type, DEFAULT_TEMPLATES.get("erstkontakt"))
            variables = {
                "firma": lead.firma or "",
                "stadt": lead.stadt or "",
                "website": lead.website or "",
                "ranking_grade": lead.ranking_grade or "?",
                "ranking_score": str(lead.ranking_score or "?"),
                "absender_name": sig_text.split("\n")[0] if sig_text else "AidSec Team",
                "produkt": product.get("name", ""),
                "preis": product.get("preis", ""),
            }

            betreff = email_svc.render_template(tpl["betreff"], variables)
            inhalt = email_svc.render_template(tpl["inhalt"], variables)

            status_text.text(f"Sende an {lead.firma} ({i+1}/{len(due_cls)})...")

            result = email_svc.send_email(to_email=lead.email, subject=betreff, body=inhalt)

            if result.get("success"):
                sent += 1
                eh = EmailHistory(
                    lead_id=lead.id, betreff=betreff, inhalt=inhalt,
                    status=EmailStatus.SENT, gesendet_at=datetime.utcnow(),
                    campaign_id=campaign.id,
                )
                session.add(eh)
                if lead.status == LeadStatus.OFFEN:
                    old = lead.status
                    lead.status = LeadStatus.PENDING
                    session.add(StatusHistory(lead_id=lead.id, von_status=old, zu_status=LeadStatus.PENDING))
                _advance_campaign_lead(cl, seq)
                session.flush()
            else:
                errors += 1
                session.add(EmailHistory(
                    lead_id=lead.id, betreff=betreff, inhalt=inhalt,
                    status=EmailStatus.FAILED, campaign_id=campaign.id,
                ))
                session.flush()

            progress.progress((i + 1) / len(due_cls))
            if i < len(due_cls) - 1:
                time.sleep(delay)

        session.commit()
        status_text.empty()
        progress.empty()
        st.success(f"Fertig! {sent} gesendet, {errors} Fehler.")
        if "kampagne_send_id" in st.session_state:
            del st.session_state["kampagne_send_id"]
        st.rerun()


def _advance_campaign_lead(cl: CampaignLead, seq: list):
    next_step = cl.current_step + 1
    if next_step >= len(seq):
        cl.cl_status = "abgeschlossen"
        cl.next_send_at = None
    else:
        cl.current_step = next_step
        delay = seq[next_step].get("delay_tage", 3)
        cl.next_send_at = datetime.utcnow() + timedelta(days=delay)


def _render_analytics():
    session = get_session()
    try:
        campaigns = session.query(Campaign).all()

        if not campaigns:
            st.info("Keine Kampagnen für Analyse vorhanden.")
            return

        st.subheader("Kampagnen-Vergleich")

        rows = []
        for camp in campaigns:
            n_leads = len(camp.campaign_leads)
            n_done = sum(1 for cl in camp.campaign_leads if cl.cl_status == "abgeschlossen")
            emails_sent = session.query(func.count(EmailHistory.id)).filter(
                EmailHistory.campaign_id == camp.id,
                EmailHistory.status == EmailStatus.SENT,
            ).scalar() or 0

            lead_ids = [cl.lead_id for cl in camp.campaign_leads]
            won = 0
            if lead_ids:
                won = session.query(Lead).filter(
                    Lead.id.in_(lead_ids),
                    Lead.status == LeadStatus.GEWONNEN,
                ).count()

            conv_rate = round(won / max(1, n_leads) * 100, 1)
            rows.append({
                "Kampagne": camp.name,
                "Status": STATUS_BADGE.get(camp.status, ("?",))[0],
                "Leads": n_leads,
                "Emails": emails_sent,
                "Abgeschlossen": n_done,
                "Gewonnen": won,
                "Conversion %": conv_rate,
            })

        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.subheader("Kampagnen-Funnel")
        all_cls = session.query(CampaignLead).all()
        all_lead_ids = list({cl.lead_id for cl in all_cls})

        if all_lead_ids:
            total_in_camp = len(all_lead_ids)
            step_0_done = sum(1 for cl in all_cls if cl.current_step >= 1 or cl.cl_status == "abgeschlossen")
            step_1_done = sum(1 for cl in all_cls if cl.current_step >= 2 or cl.cl_status == "abgeschlossen")
            step_2_done = sum(1 for cl in all_cls if cl.cl_status == "abgeschlossen")
            won_count = session.query(Lead).filter(
                Lead.id.in_(all_lead_ids),
                Lead.status == LeadStatus.GEWONNEN,
            ).count()

            fig = go.Figure(go.Funnel(
                y=["Leads in Kampagnen", "Erstkontakt gesendet",
                   "Nachfassen gesendet", "Angebot gesendet", "Gewonnen"],
                x=[total_in_camp, step_0_done, step_1_done, step_2_done, won_count],
                marker=dict(color=["#3498db", "#00d4aa", "#f39c12", "#2ecc71", "#27ae60"]),
                textinfo="value+percent initial",
                textfont=dict(family="JetBrains Mono", size=13, color="#e8eaed"),
            ))
            fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
            st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)

        st.markdown("---")
        st.subheader("Kampagnen-Emails pro Tag")
        camp_emails = session.query(EmailHistory).filter(
            EmailHistory.campaign_id.isnot(None),
            EmailHistory.status == EmailStatus.SENT,
        ).all()

        if camp_emails:
            by_day = {}
            for eh in camp_emails:
                d = eh.gesendet_at.date() if eh.gesendet_at else None
                if d:
                    by_day[d] = by_day.get(d, 0) + 1

            if by_day:
                df_days = pd.DataFrame(sorted(by_day.items()), columns=["Datum", "Emails"])
                fig = px.bar(df_days, x="Datum", y="Emails", color_discrete_sequence=["#00d4aa"])
                fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
                st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)
        else:
            st.info("Noch keine Kampagnen-Emails gesendet.")
    finally:
        session.close()
