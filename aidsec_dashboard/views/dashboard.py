"""Dashboard Page — powered by API"""
import streamlit as st
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import api_client
from cache_helpers import cached_dashboard_kpis

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Sans, sans-serif", color="#e8eaed"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
    yaxis=dict(gridcolor="#2a3040", zerolinecolor="#2a3040"),
)

PLOTLY_CONFIG = {"displayModeBar": False}

STATUS_COLORS = {"Offen": "#3498db", "Pending": "#f39c12", "Gewonnen": "#2ecc71", "Verloren": "#e74c3c"}
KATEGORIE_COLORS = ["#00d4aa", "#f0a500", "#7f8c8d"]


def render():
    st.title("📊 Dashboard")

    try:
        kpis = cached_dashboard_kpis()
    except Exception as e:
        st.error(f"API nicht erreichbar: {e}")
        st.info("Bitte sicherstellen, dass der API-Server läuft (start.bat).")
        return

    s = kpis["status"]
    if s["total"] == 0:
        st.warning("Keine Leads vorhanden!")
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Leads", s["total"])
    c2.metric("Offen", s["offen"])
    c3.metric("Pending", s["pending"])
    c4.metric("Gewonnen", s["gewonnen"])
    c5.metric("Verloren", s["verloren"])

    st.markdown("---")

    w = kpis["weekly"]
    dc1, dc2, dc3 = st.columns(3)
    dc1.metric("Neu diese Woche", w["new_this_week"])
    dc2.metric("Gewonnen diese Woche", w["won_this_week"])
    dc3.metric("Verloren diese Woche", w["lost_this_week"])

    conv = kpis["conversion"]
    fc1, fc2 = st.columns(2)
    fc1.metric("Kontaktiert-Rate", f"{conv['kontaktiert_rate']}%", help="Anteil Leads die über 'Offen' hinaus sind")
    fc2.metric("Gewinn-Rate", f"{conv['gewinn_rate']}%", help="Gewonnen / (Gewonnen + Verloren)")

    st.markdown("---")

    # Charts
    k = kpis["kategorie"]
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Nach Kategorie")
        fig = px.pie(
            values=[k["anwalt"], k["praxis"], k["wordpress"]],
            names=["Anwälte", "Praxen", "WordPress"],
            color_discrete_sequence=KATEGORIE_COLORS,
            hole=0.45,
        )
        fig.update_layout(**PLOTLY_LAYOUT)
        fig.update_traces(textfont=dict(family="JetBrains Mono", size=12))
        st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)

    with c2:
        st.subheader("Nach Status")
        labels = list(STATUS_COLORS.keys())
        values = [s["offen"], s["pending"], s["gewonnen"], s["verloren"]]
        colors = list(STATUS_COLORS.values())
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            marker_color=colors,
            marker_line=dict(width=0),
            text=values,
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=13, color="#e8eaed"),
        ))
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        fig.update_yaxes(showgrid=True)
        st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)

    # Ranking distribution
    g = kpis["grades"]
    grade_colors_map = {"A": "#2ecc71", "B": "#f1c40f", "C": "#e67e22", "D": "#e74c3c", "F": "#c0392b"}
    has_rankings = sum(g.values()) > 0
    if has_rankings:
        st.subheader("Ranking-Verteilung")
        grades = list(grade_colors_map.keys())
        counts = [g.get(gr, 0) for gr in grades]
        colors = [grade_colors_map[gr] for gr in grades]
        fig = go.Figure(go.Bar(
            x=grades, y=counts,
            marker_color=colors,
            marker_line=dict(width=0),
            text=counts,
            textposition="outside",
            textfont=dict(family="JetBrains Mono", size=13, color="#e8eaed"),
        ))
        fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        fig.update_yaxes(showgrid=True)
        st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)

    # Follow-up widget
    st.markdown("---")
    _render_followup_widget(kpis["followups"])

    # Conversion Funnel
    st.markdown("---")
    _render_conversion_funnel(s)

    # Email Stats
    st.markdown("---")
    _render_email_stats(kpis["email_stats"])

    # Campaign KPIs
    camp = kpis["campaign"]
    if camp["total_campaigns"] > 0:
        st.markdown("---")
        _render_campaign_kpis(camp)

    # Marketing KPIs
    mkt = kpis["marketing"]
    if mkt["total"] > 0:
        st.markdown("---")
        _render_marketing_kpis(mkt)

    # Recent leads
    st.markdown("---")
    col_title, col_count = st.columns([3, 1])
    with col_title:
        st.subheader("Neueste Leads")
    with col_count:
        n_recent = st.selectbox("Anzahl", [10, 20, 50], index=1, key="recent_count")

    try:
        result = api_client.get_leads(page=1, per_page=n_recent, sort="newest")
        items = result.get("items", [])
        if items:
            data = []
            for l in items:
                data.append({
                    "Firma": l["firma"],
                    "Stadt": l.get("stadt") or "-",
                    "Kategorie": l.get("kategorie", "-"),
                    "Status": l.get("status", "-"),
                    "Ranking": l.get("ranking_grade") or "-",
                })
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception:
        pass


def _render_followup_widget(fu):
    st.subheader("📅 Anstehende Follow-ups")

    fc1, fc2, fc3 = st.columns(3)
    fc1.metric("Überfällig", fu["overdue"])
    fc2.metric("Heute", fu["today"])
    fc3.metric("Geplant", fu["upcoming"])

    try:
        pending = api_client.get_followups(due="pending")
        if not pending:
            st.info("Keine offenen Follow-ups.")
            return
        for item in pending[:15]:
            d = item.get("datum", "-")
            if isinstance(d, str) and "T" in d:
                d = d.split("T")[0]
                parts = d.split("-")
                if len(parts) == 3:
                    d = f"{parts[2]}.{parts[1]}.{parts[0]}"
            firma = item.get("lead_firma", "?")
            notiz = item.get("notiz", "")
            color = "#e74c3c" if item.get("overdue") else "#b8bec6"
            col_info, col_done = st.columns([5, 1])
            with col_info:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;'
                    f'padding:4px 0;border-bottom:1px solid #2a304033;">'
                    f'<span style="color:{color};font-weight:600;font-family:JetBrains Mono,monospace;'
                    f'font-size:0.85rem;min-width:80px;">{d}</span>'
                    f'<span style="font-weight:500;">{firma}</span>'
                    f'<span style="color:#b8bec6;font-size:0.85rem;">{notiz}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_done:
                if st.button("✅", key=f"fu_done_{item['id']}"):
                    try:
                        api_client.update_followup(item["id"], erledigt=True)
                        st.rerun()
                    except Exception:
                        pass
    except Exception:
        st.info("Keine offenen Follow-ups.")


def _render_conversion_funnel(s):
    st.subheader("Conversion Funnel")

    total = s["total"]
    if total == 0:
        st.info("Keine Leads vorhanden.")
        return

    fig = go.Figure(go.Funnel(
        y=["Offen", "Pending", "Gewonnen"],
        x=[total, s["pending"] + s["gewonnen"] + s["verloren"], s["gewonnen"]],
        marker=dict(color=["#3498db", "#f39c12", "#2ecc71"]),
        textinfo="value+percent initial",
        textfont=dict(family="JetBrains Mono", size=13, color="#e8eaed"),
    ))
    fig.update_layout(**PLOTLY_LAYOUT, showlegend=False)
    st.plotly_chart(fig, config=PLOTLY_CONFIG, use_container_width=True)


def _render_email_stats(es):
    st.subheader("📧 E-Mail Performance")

    ec1, ec2, ec3, ec4 = st.columns(4)
    ec1.metric("Gesamt gesendet", es["total_sent"])
    ec2.metric("Leads kontaktiert", es["leads_contacted"])
    ec3.metric("Ø pro Lead", es["avg_per_lead"])
    ec4.metric("Erfolgsquote", f"{es['success_rate']}%", help="Kontaktierte Leads die 'Gewonnen' wurden")


def _render_campaign_kpis(camp):
    st.subheader("🎯 Kampagnen")

    kc1, kc2, kc3, kc4, kc5 = st.columns(5)
    kc1.metric("Kampagnen", camp["total_campaigns"])
    kc2.metric("Aktive", camp["active_campaigns"])
    kc3.metric("Leads in Kampagnen", camp["leads_in_campaigns"])
    kc4.metric("Fällige Emails", camp["due_emails"])
    kc5.metric("Kampagnen-Emails", camp["campaign_emails_sent"])


def _render_marketing_kpis(mkt):
    st.subheader("💡 Marketing Strategie")

    mk1, mk2, mk3, mk4 = st.columns(4)
    mk1.metric("Ideen gesamt", mkt["total"])
    mk2.metric("Geplant", mkt["planned"])
    mk3.metric("In Umsetzung", mkt["active"])
    mk4.metric("Abgeschlossen", mkt["completed"])

    if mkt["total"] > 0:
        progress = mkt["completed"] / mkt["total"]
        st.progress(progress, text=f"Fortschritt: {mkt['completed']}/{mkt['total']} Ideen abgeschlossen")
