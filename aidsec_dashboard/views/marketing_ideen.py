"""Marketing Ideen — Browse, AI-Recommend, Track — powered by API"""
import streamlit as st
import api_client
from cache_helpers import cached_marketing_tracker, invalidate_marketing
from services.marketing_ideas import (
    MARKETING_IDEAS, IDEA_CATEGORIES, BUDGET_LABELS, TIMELINE_LABELS,
    STAGE_LABELS, filter_ideas, get_idea_by_nr,
)
from services.outreach import parse_llm_json

BUDGET_COLORS = {"free": "#2ecc71", "low": "#3498db", "medium": "#f39c12", "high": "#e74c3c"}
PRIO_BADGE = {
    1: ("Hoch", "#e74c3c", "#e74c3c35"),
    2: ("Mittel", "#f39c12", "#f39c1235"),
    3: ("Niedrig", "#3498db", "#3498db35"),
}
STATUS_CONF = {
    "geplant": ("Geplant", "#b8bec6", "#b8bec635"),
    "aktiv": ("Aktiv", "#2ecc71", "#2ecc7135"),
    "abgeschlossen": ("Erledigt", "#00d4aa", "#00d4aa35"),
    "verworfen": ("Verworfen", "#7f8c8d", "#7f8c8d35"),
}


def render():
    st.title("💡 Marketing Ideen")
    st.caption("140 bewährte Marketing-Strategien — durchsuchen, filtern, KI-Empfehlungen und Umsetzungs-Tracking")

    tab_browse, tab_ai, tab_strategy = st.tabs([
        "Ideen-Browser", "KI-Empfehlung", "Meine Strategie",
    ])

    with tab_browse:
        _render_browser()
    with tab_ai:
        _render_ai_recommendation()
    with tab_strategy:
        _render_strategy()


def _render_browser():
    fc1, fc2, fc3, fc4 = st.columns([3, 2, 2, 2])
    with fc1:
        search = st.text_input("Suche", placeholder="z.B. LinkedIn, SEO, Newsletter...", key="mi_search")
    with fc2:
        sel_cats = st.multiselect("Kategorie", IDEA_CATEGORIES, key="mi_cats")
    with fc3:
        sel_budget = st.multiselect("Budget", list(BUDGET_LABELS.keys()),
                                    format_func=lambda x: BUDGET_LABELS[x], key="mi_budget")
    with fc4:
        sel_stages = st.multiselect("Phase", list(STAGE_LABELS.keys()),
                                    format_func=lambda x: STAGE_LABELS[x], key="mi_stages")

    ideas = filter_ideas(
        categories=sel_cats or None,
        budgets=sel_budget or None,
        stages=sel_stages or None,
        search=search,
    )

    st.markdown(
        f"<div style='margin:8px 0 16px 0;color:#b8bec6;font-size:0.85rem;'>"
        f"<b>{len(ideas)}</b> von {len(MARKETING_IDEAS)} Ideen"
        f"</div>",
        unsafe_allow_html=True,
    )

    try:
        tracker_list = cached_marketing_tracker()
        tracked = {t["idea_number"]: t["status"] for t in tracker_list}
    except Exception:
        tracked = {}

    for idx in range(0, len(ideas), 2):
        cols = st.columns(2)
        for ci, col in enumerate(cols):
            i_idx = idx + ci
            if i_idx >= len(ideas):
                break
            idea = ideas[i_idx]
            with col:
                _render_idea_card(idea, tracked.get(idea["nr"]))


def _render_idea_card(idea: dict, tracked_status: str = None):
    nr = idea["nr"]
    budget_color = BUDGET_COLORS.get(idea["budget"], "#b8bec6")
    budget_label = BUDGET_LABELS.get(idea["budget"], idea["budget"])
    time_label = TIMELINE_LABELS.get(idea["time"], idea["time"])
    stage_labels = ", ".join(STAGE_LABELS.get(s, s) for s in idea["stages"])

    status_html = ""
    if tracked_status:
        s_label, s_color, s_bg = STATUS_CONF.get(tracked_status, STATUS_CONF["geplant"])
        status_html = (
            f'<span style="background:{s_bg};color:{s_color};border:1px solid {s_color}44;'
            f'padding:2px 8px;border-radius:10px;font-size:0.78rem;font-weight:600;'
            f'margin-left:8px;">{s_label}</span>'
        )

    st.markdown(
        f'<div style="background:#1a1f2e;border:1px solid #2a3040;border-radius:8px;'
        f'padding:14px 16px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span style="background:#00d4aa35;color:#00d4aa;border:1px solid #00d4aa44;'
        f'padding:2px 8px;border-radius:10px;font-size:0.8rem;font-weight:700;'
        f'font-family:JetBrains Mono,monospace;">#{nr}</span>'
        f'<span style="font-weight:600;font-size:0.95rem;color:#e8eaed;">{idea["name"]}</span>'
        f'{status_html}'
        f'</div>'
        f'<div style="color:#b8bec6;font-size:0.85rem;margin-bottom:8px;">{idea["desc"]}</div>'
        f'<div style="display:flex;flex-wrap:wrap;gap:6px;">'
        f'<span style="background:#2a3040;color:#e8eaed;padding:2px 8px;border-radius:8px;'
        f'font-size:0.78rem;">{idea["cat"]}</span>'
        f'<span style="background:{budget_color}35;color:{budget_color};padding:2px 8px;'
        f'border-radius:8px;font-size:0.78rem;border:1px solid {budget_color}44;">'
        f'{budget_label}</span>'
        f'<span style="background:#2a3040;color:#b8bec6;padding:2px 8px;border-radius:8px;'
        f'font-size:0.78rem;">{time_label}</span>'
        f'<span style="background:#2a3040;color:#b8bec6;padding:2px 8px;border-radius:8px;'
        f'font-size:0.78rem;">{stage_labels}</span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    with st.expander(f"Details und Umsetzung -- Nr. {nr}", expanded=False):
        if idea.get("how"):
            st.markdown("**Erste Schritte:**")
            for step in idea["how"]:
                st.markdown(f"- {step}")
        if idea.get("aidsec"):
            st.markdown(f"**AidSec-Relevanz:** {idea['aidsec']}")

        if not tracked_status:
            if st.button("Zur Strategie hinzufügen", key=f"add_{nr}", type="primary"):
                try:
                    api_client.add_to_tracker(nr)
                    invalidate_marketing()
                    st.rerun()
                except Exception as e:
                    st.error(str(e))
        else:
            st.info(f"Status: {STATUS_CONF.get(tracked_status, ('?',))[0]}")


def _render_ai_recommendation():
    st.subheader("KI-gestützte Marketing-Empfehlung")
    st.markdown(
        "Die KI analysiert deine aktuelle Pipeline-Situation und empfiehlt die "
        "relevantesten Marketing-Ideen basierend auf Ressourcen, Prioritäten und ROI-Potenzial."
    )

    if st.button("Analysiere meine Situation & empfehle Ideen", type="primary", key="ai_rec"):
        with st.spinner("KI analysiert deine Pipeline und wählt die besten Ideen..."):
            try:
                result = api_client.recommend_marketing()
                if isinstance(result, list):
                    st.session_state["mi_recommendations"] = result
                elif isinstance(result, dict):
                    if result.get("recommendations"):
                        st.session_state["mi_recommendations"] = result["recommendations"]
                    elif "error" in result:
                        st.error(f"Fehler: {result['error']}")
                    else:
                        st.session_state["mi_recommendations"] = [result]
            except api_client.APIError as e:
                st.error(f"Fehler: {e.detail}")
            except Exception as e:
                st.error(f"Fehler: {e}")

    if "mi_recommendations" in st.session_state:
        recs = st.session_state["mi_recommendations"]
        st.markdown("---")
        st.markdown(
            f'<div style="background:#00d4aa15;border:1px solid #00d4aa33;border-radius:8px;'
            f'padding:12px 16px;margin-bottom:16px;">'
            f'<span style="color:#00d4aa;font-weight:600;">KI-Analyse abgeschlossen</span> — '
            f'<span style="color:#b8bec6;">{len(recs)} Empfehlungen basierend auf deiner Pipeline</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for rec in recs:
            idea = get_idea_by_nr(rec.get("nr", 0))
            if not idea:
                continue
            _render_recommendation_card(idea, rec)


def _render_recommendation_card(idea: dict, rec: dict):
    nr = idea["nr"]
    prio = rec.get("prioritaet", "mittel")
    prio_int = 1 if prio == "hoch" else 2
    p_label, p_color, p_bg = PRIO_BADGE.get(prio_int, PRIO_BADGE[2])

    st.markdown(
        f'<div style="background:#1a1f2e;border:1px solid #00d4aa44;border-left:3px solid #00d4aa;'
        f'border-radius:8px;padding:14px 16px;margin-bottom:10px;">'
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        f'<span style="background:#00d4aa35;color:#00d4aa;padding:2px 8px;border-radius:10px;'
        f'font-size:0.8rem;font-weight:700;font-family:JetBrains Mono,monospace;">#{nr}</span>'
        f'<span style="font-weight:600;font-size:0.95rem;color:#e8eaed;">{idea["name"]}</span>'
        f'<span style="background:{p_bg};color:{p_color};border:1px solid {p_color}44;'
        f'padding:2px 8px;border-radius:10px;font-size:0.78rem;font-weight:600;">{p_label}</span>'
        f'</div>'
        f'<div style="color:#e8eaed;font-size:0.85rem;margin-bottom:6px;">'
        f'{rec.get("warum", "")}</div>'
        f'<div style="color:#00d4aa;font-size:0.85rem;">'
        f'<b>Erster Schritt:</b> {rec.get("erster_schritt", "-")}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button(f"Umsetzen — #{nr}", key=f"rec_add_{nr}"):
        try:
            api_client.add_to_tracker(nr, prioritaet=prio_int)
            invalidate_marketing()
            st.rerun()
        except Exception:
            pass


def _render_strategy():
    try:
        trackers = cached_marketing_tracker()
    except Exception:
        trackers = []

    geplant = [t for t in trackers if t.get("status") == "geplant"]
    aktiv = [t for t in trackers if t.get("status") == "aktiv"]
    done = [t for t in trackers if t.get("status") == "abgeschlossen"]
    verworfen = [t for t in trackers if t.get("status") == "verworfen"]

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Geplant", len(geplant))
    mc2.metric("Aktiv", len(aktiv))
    mc3.metric("Abgeschlossen", len(done))
    mc4.metric("Verworfen", len(verworfen))

    if not trackers:
        st.info("Noch keine Ideen zur Strategie hinzugefügt. Nutze den Ideen-Browser oder die KI-Empfehlung.")
        return

    st.markdown("---")

    col_geplant, col_aktiv, col_done = st.columns(3)

    with col_geplant:
        st.markdown(
            '<div style="border-bottom:3px solid #b8bec6;padding-bottom:4px;margin-bottom:12px;'
            'font-weight:700;color:#b8bec6;">GEPLANT</div>',
            unsafe_allow_html=True,
        )
        for t in geplant:
            _render_strategy_card(t)

    with col_aktiv:
        st.markdown(
            '<div style="border-bottom:3px solid #2ecc71;padding-bottom:4px;margin-bottom:12px;'
            'font-weight:700;color:#2ecc71;">AKTIV</div>',
            unsafe_allow_html=True,
        )
        for t in aktiv:
            _render_strategy_card(t)

    with col_done:
        st.markdown(
            '<div style="border-bottom:3px solid #00d4aa;padding-bottom:4px;margin-bottom:12px;'
            'font-weight:700;color:#00d4aa;">ABGESCHLOSSEN</div>',
            unsafe_allow_html=True,
        )
        for t in done:
            _render_strategy_card(t)

    if verworfen:
        with st.expander(f"Verworfene Ideen ({len(verworfen)})"):
            for t in verworfen:
                idea = get_idea_by_nr(t.get("idea_number", 0))
                if idea:
                    st.markdown(f"~~#{t['idea_number']} {idea['name']}~~")


def _render_strategy_card(tracker: dict):
    nr = tracker.get("idea_number", 0)
    idea = get_idea_by_nr(nr)
    if not idea:
        return

    prio = tracker.get("prioritaet", 2)
    p_label, p_color, p_bg = PRIO_BADGE.get(prio, PRIO_BADGE[2])

    st.markdown(
        f'<div style="background:#1a1f2e;border:1px solid #2a3040;border-radius:8px;'
        f'padding:10px 12px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
        f'<span style="color:#00d4aa;font-weight:700;font-size:0.8rem;'
        f'font-family:JetBrains Mono,monospace;">#{nr}</span>'
        f'<span style="font-weight:600;font-size:0.85rem;color:#e8eaed;">{idea["name"]}</span>'
        f'</div>'
        f'<span style="background:{p_bg};color:{p_color};border:1px solid {p_color}44;'
        f'padding:1px 6px;border-radius:8px;font-size:0.78rem;font-weight:600;">{p_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander(f"Bearbeiten -- Nr. {nr}", expanded=False):
        current_status = tracker.get("status", "geplant")
        all_statuses = ["geplant", "aktiv", "abgeschlossen", "verworfen"]
        new_status = st.selectbox(
            "Status",
            all_statuses,
            index=all_statuses.index(current_status) if current_status in all_statuses else 0,
            key=f"strat_status_{nr}",
        )
        new_prio = st.selectbox(
            "Priorität",
            [1, 2, 3],
            index=[1, 2, 3].index(prio) if prio in [1, 2, 3] else 1,
            format_func=lambda x: PRIO_BADGE[x][0],
            key=f"strat_prio_{nr}",
        )
        new_notes = st.text_area(
            "Notizen",
            value=tracker.get("notizen") or "",
            key=f"strat_notes_{nr}",
        )

        if st.button("Speichern", key=f"strat_save_{nr}", type="primary"):
            try:
                api_client.update_tracker(
                    tracker["id"],
                    status=new_status,
                    prioritaet=new_prio,
                    notizen=new_notes,
                )
                invalidate_marketing()
                st.rerun()
            except Exception as e:
                st.error(str(e))
