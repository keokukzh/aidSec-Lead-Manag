"""Leads Page — powered by API"""
import streamlit as st
import api_client

SORT_OPTIONS = {
    "Neueste zuerst": "newest",
    "Älteste zuerst": "oldest",
    "Firma A-Z": "firma_asc",
    "Firma Z-A": "firma_desc",
    "Ranking aufsteigend": "ranking_asc",
    "Ranking absteigend": "ranking_desc",
}

STATUS_BADGE = {
    "offen": '<span class="status-badge badge-offen">offen</span>',
    "pending": '<span class="status-badge badge-pending">pending</span>',
    "gewonnen": '<span class="status-badge badge-gewonnen">gewonnen</span>',
    "verloren": '<span class="status-badge badge-verloren">verloren</span>',
}

ALL_STATUSES = ["offen", "pending", "gewonnen", "verloren"]


def _status_dot(status_val):
    colors = {"offen": "#3498db", "pending": "#f39c12", "gewonnen": "#2ecc71", "verloren": "#e74c3c"}
    c = colors.get(status_val, "#b8bec6")
    return f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{c};margin-right:6px;vertical-align:middle;"></span>'


def render():
    st.title("📋 Leads Verwaltung")

    # Add Lead expander
    with st.expander("➕ Neuen Lead hinzufügen", expanded=False):
        with st.form("add_lead_form"):
            col1, col2 = st.columns(2)
            with col1:
                firma = st.text_input("Firma *", placeholder="Firmenname")
                email = st.text_input("E-Mail", placeholder="email@beispiel.de")
                telefon = st.text_input("Telefon", placeholder="+41 79...")
            with col2:
                website = st.text_input("Website", placeholder="https://...")
                stadt = st.text_input("Stadt", placeholder="Zürich")
                kategorie = st.selectbox("Kategorie", ["anwalt", "praxis", "wordpress"])

            quelle = st.text_input("Quelle", placeholder="z.B. LinkedIn, Messe, etc.")

            submitted = st.form_submit_button("Lead speichern", type="primary")

            if submitted:
                if not firma:
                    st.error("Firma ist erforderlich")
                else:
                    try:
                        api_client.create_lead(
                            firma=firma,
                            website=website or None,
                            email=email or None,
                            telefon=telefon or None,
                            stadt=stadt or None,
                            kategorie=kategorie,
                            quelle=quelle or None,
                        )
                        st.success(f"Lead '{firma}' erfolgreich erstellt!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Fehler beim Erstellen: {e}")

    try:
        check = api_client.get_leads(page=1, per_page=1)
    except Exception as e:
        st.error(f"API nicht erreichbar: {e}")
        return

    if check.get("total", 0) == 0:
        st.warning("Keine Leads vorhanden. Bitte importieren Sie zuerst Leads.")
        return

    view = st.radio("Ansicht:", ["📋 Liste", "🔄 Pipeline"], horizontal=True)

    if view == "🔄 Pipeline":
        render_pipeline()
    else:
        render_list()


def render_pipeline():
    try:
        pipeline = api_client.get_leads_pipeline(per_status=100)
    except Exception:
        pipeline = {}
    buckets = {}
    bucket_totals = {}
    for s in ALL_STATUSES:
        bucket_data = pipeline.get(s, {})
        buckets[s] = bucket_data.get("items", []) if isinstance(bucket_data, dict) else []
        bucket_totals[s] = bucket_data.get("total", len(buckets[s])) if isinstance(bucket_data, dict) else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Offen", bucket_totals["offen"])
    c2.metric("Pending", bucket_totals["pending"])
    c3.metric("Gewonnen", bucket_totals["gewonnen"])
    c4.metric("Verloren", bucket_totals["verloren"])

    st.markdown("---")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown('<div class="pipeline-header pipeline-header-offen">OFFEN</div>', unsafe_allow_html=True)
        for l in buckets["offen"][:50]:
            with st.container(border=True):
                if st.button(f"**{l['firma'][:30]}**", key=f"open_{l['id']}"):
                    st.session_state["selected_lead_id"] = l["id"]
                    st.rerun()
                if l.get("stadt"):
                    st.caption(l["stadt"])
                if st.button("→ Pending", key=f"p_{l['id']}"):
                    _update_status_api(l["id"], "pending")
                    st.rerun()
        if len(buckets["offen"]) > 50:
            with st.expander(f"Alle anzeigen ({len(buckets['offen'])} total)"):
                for l in buckets["offen"][50:]:
                    if st.button(f"{l['firma']} ({l.get('stadt') or '-'})", key=f"open_ex_{l['id']}"):
                        st.session_state["selected_lead_id"] = l["id"]
                        st.rerun()

    with c2:
        st.markdown('<div class="pipeline-header pipeline-header-pending">PENDING</div>', unsafe_allow_html=True)
        for l in buckets["pending"][:50]:
            with st.container(border=True):
                if st.button(f"**{l['firma'][:30]}**", key=f"popen_{l['id']}"):
                    st.session_state["selected_lead_id"] = l["id"]
                    st.rerun()
                if l.get("stadt"):
                    st.caption(l["stadt"])
                ca, cb = st.columns(2)
                with ca:
                    if st.button("✓", key=f"gw_{l['id']}"):
                        _update_status_api(l["id"], "gewonnen")
                        st.rerun()
                with cb:
                    if st.button("✗", key=f"vl_{l['id']}"):
                        _update_status_api(l["id"], "verloren")
                        st.rerun()
        if len(buckets["pending"]) > 50:
            with st.expander(f"Alle anzeigen ({len(buckets['pending'])} total)"):
                for l in buckets["pending"][50:]:
                    if st.button(f"{l['firma']} ({l.get('stadt') or '-'})", key=f"popen_ex_{l['id']}"):
                        st.session_state["selected_lead_id"] = l["id"]
                        st.rerun()

    with c3:
        st.markdown('<div class="pipeline-header pipeline-header-gewonnen">GEWONNEN</div>', unsafe_allow_html=True)
        for l in buckets["gewonnen"][:50]:
            with st.container(border=True):
                if st.button(f"**{l['firma'][:30]}**", key=f"gopen_{l['id']}"):
                    st.session_state["selected_lead_id"] = l["id"]
                    st.rerun()
                if l.get("stadt"):
                    st.caption(l["stadt"])
        if len(buckets["gewonnen"]) > 50:
            with st.expander(f"Alle anzeigen ({len(buckets['gewonnen'])} total)"):
                for l in buckets["gewonnen"][50:]:
                    if st.button(f"{l['firma']} ({l.get('stadt') or '-'})", key=f"gopen_ex_{l['id']}"):
                        st.session_state["selected_lead_id"] = l["id"]
                        st.rerun()

    with c4:
        st.markdown('<div class="pipeline-header pipeline-header-verloren">VERLOREN</div>', unsafe_allow_html=True)
        for l in buckets["verloren"][:50]:
            with st.container(border=True):
                if st.button(f"**{l['firma'][:30]}**", key=f"vopen_{l['id']}"):
                    st.session_state["selected_lead_id"] = l["id"]
                    st.rerun()
                if l.get("stadt"):
                    st.caption(l["stadt"])
        if len(buckets["verloren"]) > 50:
            with st.expander(f"Alle anzeigen ({len(buckets['verloren'])} total)"):
                for l in buckets["verloren"][50:]:
                    if st.button(f"{l['firma']} ({l.get('stadt') or '-'})", key=f"vopen_ex_{l['id']}"):
                        st.session_state["selected_lead_id"] = l["id"]
                        st.rerun()


def render_list():
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        search = st.text_input("🔍 Suche", placeholder="Firma, E-Mail, Stadt...")
    with c2:
        f_status = st.selectbox("Status", ["Alle", "offen", "pending", "gewonnen", "verloren"])
    with c3:
        f_kategorie = st.selectbox("Kategorie", ["Alle", "anwalt", "praxis", "wordpress"])
    with c4:
        sort_key = st.selectbox("Sortierung", list(SORT_OPTIONS.keys()))

    page_sizes = [25, 50, 100]
    col_ps, col_nav = st.columns([1, 3])
    with col_ps:
        page_size = st.selectbox("Pro Seite", page_sizes, index=1, key="page_size")

    if "leads_page" not in st.session_state:
        st.session_state.leads_page = 0

    page = st.session_state.leads_page + 1

    try:
        result = api_client.get_leads(
            page=page,
            per_page=page_size,
            status=f_status if f_status != "Alle" else None,
            kategorie=f_kategorie if f_kategorie != "Alle" else None,
            search=search if search else None,
            sort=SORT_OPTIONS[sort_key],
        )
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return

    total_count = result.get("total", 0)
    items = result.get("items", [])
    max_page = max(0, (total_count - 1) // page_size)
    if st.session_state.leads_page > max_page:
        st.session_state.leads_page = max_page

    with col_nav:
        nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([1, 1, 2, 2])
        with nav_c1:
            if st.button("◀ Zurück", disabled=st.session_state.leads_page == 0):
                st.session_state.leads_page -= 1
                st.rerun()
        with nav_c2:
            if st.button("Weiter ▶", disabled=st.session_state.leads_page >= max_page):
                st.session_state.leads_page += 1
                st.rerun()
        with nav_c3:
            st.markdown(
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#b8bec6;">'
                f'Seite <b style="color:#e8eaed;">{st.session_state.leads_page + 1}</b> / {max_page + 1}</span>',
                unsafe_allow_html=True,
            )
        with nav_c4:
            st.markdown(
                f'<span style="font-family:JetBrains Mono,monospace;font-size:0.85rem;color:#00d4aa;font-weight:600;">'
                f'{total_count}</span> <span style="color:#b8bec6;font-size:0.85rem;">Leads</span>',
                unsafe_allow_html=True,
            )

    st.markdown("---")

    col_bulk, col_export = st.columns([2, 1])
    with col_bulk:
        bulk_status = st.selectbox(
            "Bulk-Aktion: Status ändern",
            ["-- Keine --"] + ALL_STATUSES,
            key="bulk_action",
        )
    with col_export:
        if total_count > 0:
            ec1, ec2 = st.columns(2)
            with ec1:
                try:
                    csv_data = api_client.export_csv(
                        status=f_status if f_status != "Alle" else None,
                        kategorie=f_kategorie if f_kategorie != "Alle" else None,
                    )
                    st.download_button("📥 CSV", csv_data, "leads_export.csv", "text/csv")
                except Exception:
                    st.button("📥 CSV", disabled=True)
            with ec2:
                try:
                    xlsx_data = api_client.export_excel(
                        status=f_status if f_status != "Alle" else None,
                        kategorie=f_kategorie if f_kategorie != "Alle" else None,
                    )
                    st.download_button(
                        "📥 Excel", xlsx_data, "leads_export.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                except Exception:
                    st.button("📥 Excel", disabled=True)

    if items:
        selected_ids = []
        for i, l in enumerate(items):
            row_class = "lead-row-even" if i % 2 == 0 else ""
            col_cb, col_info, col_open = st.columns([0.3, 5, 0.8])
            with col_cb:
                if st.checkbox("", key=f"sel_{l['id']}", label_visibility="collapsed"):
                    selected_ids.append(l["id"])
            with col_info:
                sv = l.get("status", "offen")
                badge = STATUS_BADGE.get(sv, sv)
                dot = _status_dot(sv)
                st.markdown(
                    f'<div class="lead-row {row_class}">'
                    f'{dot}<span class="lead-firma">{l["firma"]}</span>'
                    f'<span class="lead-meta"> &nbsp;|&nbsp; {l.get("stadt") or "-"} &nbsp;|&nbsp; '
                    f'{l.get("email") or "-"}</span> &nbsp; {badge}'
                    f'<span class="lead-meta" style="float:right;">{l.get("kategorie", "-")}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_open:
                if st.button("Öffnen", key=f"detail_{l['id']}"):
                    st.session_state["selected_lead_id"] = l["id"]
                    st.rerun()

        if selected_ids and bulk_status != "-- Keine --":
            if st.button(f"✅ Status für {len(selected_ids)} Leads ändern", type="primary"):
                try:
                    api_client.bulk_status(selected_ids, bulk_status)
                    st.success(f"{len(selected_ids)} Leads aktualisiert!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler: {e}")


def _update_status_api(lead_id: int, new_status: str):
    try:
        api_client.update_lead(lead_id, status=new_status)
    except Exception:
        pass
