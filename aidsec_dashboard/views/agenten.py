"""Agenten Page - LLM-powered Lead Search and Outreach — powered by API"""
import streamlit as st
import json
import pandas as pd
import io
from datetime import datetime
import api_client
from cache_helpers import cached_llm_status, cached_smtp_config, cached_email_signature
from services.llm_service import get_llm_service
from services.outreach import (
    PRODUCT_CATALOG,
    detect_email_type,
    get_recommended_product,
    EMAIL_TYPE_LABELS,
    EMAIL_TYPE_COLORS,
    parse_llm_json,
)
from views.email import render_send_confirm

BRANCHEN = [
    "Alle", "Arztpraxis", "Zahnarztpraxis", "Tierarztpraxis",
    "Anwaltskanzlei", "Steuerberater", "Treuhand", "WordPress-Agentur", "Sonstige",
]

GROESSEN = ["Alle", "Einzelpraxis / 1 Person", "2-10 Mitarbeiter", "10-50 Mitarbeiter", "50+"]

SCHMERZPUNKTE = [
    "Schlechtes Security-Ranking", "Veraltete WordPress-Version",
    "Kein HTTPS / fehlende HSTS", "nDSG-Konformität unklar",
    "Datenschutz-Bedenken", "Kein IT-Verantwortlicher",
]

SCORE_COLORS = {"high": "#2ecc71", "medium": "#f39c12", "low": "#e74c3c"}
ALL_KATEGORIEN = ["anwalt", "praxis", "wordpress"]


def _score_tier(score: int) -> str:
    if score >= 8:
        return "high"
    if score >= 5:
        return "medium"
    return "low"


def render():
    st.title("🤖 KI Agenten")
    st.markdown("Nutzen Sie KI-gestützte Agenten für Lead-Suche und Outreach.")

    try:
        llm_status = cached_llm_status()
        is_available = llm_status.get("success", False)
    except Exception:
        llm_service = get_llm_service()
        is_available = llm_service.is_available()

    if not is_available:
        st.markdown('<span class="llm-badge llm-offline">OFFLINE</span>', unsafe_allow_html=True)
        st.info(
            "**LM Studio** starten oder **OpenAI API-Key** in den Einstellungen konfigurieren.\n\n"
            "LM Studio: Herunterladen → Modell laden → Server starten.\n\n"
            "Oder: **Einstellungen** → **LLM** für OpenAI."
        )
        return

    st.markdown('<span class="llm-badge llm-online">LLM ONLINE</span>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["🔍 Lead Search Agent", "✉️ Outreach Helper", "🔬 Auto-Research"])

    with tab1:
        _render_lead_search()

    with tab2:
        _render_outreach_helper()

    with tab3:
        _render_auto_research()


def _render_lead_search():
    st.subheader("Lead Search Agent")
    st.caption("Finden Sie neue potenzielle Leads mit ICP-basierter Suche und Fit-Scoring.")

    llm_service = get_llm_service()

    with st.form("lead_search_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            stadt = st.text_input("Region / Stadt", placeholder="Zürich, Bern, ganze Schweiz...")
            kategorie = st.selectbox("Lead-Kategorie", ["Alle"] + ALL_KATEGORIEN)
            anzahl = st.slider("Anzahl Leads", 5, 30, 10)

        with col2:
            branche = st.selectbox("Branche", BRANCHEN)
            groesse = st.selectbox("Unternehmensgrösse", GROESSEN)

        with col3:
            schmerzpunkte = st.multiselect("Schmerzpunkte / Signale", SCHMERZPUNKTE)
            extra = st.text_area("Zusätzliche Kriterien", placeholder="z.B. WordPress-basiert, kürzlich in den Medien...")

        submitted = st.form_submit_button("🔍 Lead-Recherche starten", type="primary")

    if submitted:
        with st.spinner("KI recherchiert Leads..."):
            result = llm_service.search_leads(
                stadt=stadt if stadt else None,
                kategorie=kategorie if kategorie != "Alle" else None,
                branche=branche if branche != "Alle" else None,
                groesse=groesse if groesse != "Alle" else None,
                schmerzpunkte=schmerzpunkte if schmerzpunkte else None,
                anzahl=anzahl,
                extra_kriterien=extra,
            )

            if result.get("success"):
                content = result.get("content", "")
                try:
                    leads_data = parse_llm_json(content, expect_array=True)
                    if leads_data:
                        st.session_state["search_results"] = leads_data
                    else:
                        st.info("Keine Leads gefunden.")
                except (json.JSONDecodeError, ValueError):
                    st.warning("LLM-Antwort konnte nicht als JSON erkannt werden.")
                    st.text(content)
            else:
                st.error(f"Fehler: {result.get('error')}")

    if "search_results" in st.session_state and st.session_state["search_results"]:
        leads_data = st.session_state["search_results"]
        _render_search_results(leads_data, llm_service)


def _render_outreach_helper():
    st.subheader("Outreach Helper Agent")
    st.write("Lead suchen und mit KI eine personalisierte E-Mail erstellen.")

    fc1, fc2, fc3 = st.columns([3, 1, 1])
    with fc1:
        search_q = st.text_input(
            "Lead suchen",
            placeholder="Firma, Stadt oder E-Mail...",
            key="outreach_search",
        )
    with fc2:
        kat_options = {"Alle": None, "Anwalt": "anwalt", "Praxis": "praxis", "WordPress": "wordpress"}
        kat_label = st.selectbox("Kategorie", list(kat_options.keys()), key="outreach_kat")
        kat_val = kat_options[kat_label]
    with fc3:
        per_page = st.selectbox("Pro Seite", [25, 50, 100], index=0, key="outreach_pp")

    if "outreach_page" not in st.session_state:
        st.session_state["outreach_page"] = 1
    page = st.session_state["outreach_page"]

    try:
        result = api_client.get_leads(
            page=page, per_page=per_page, status="offen,pending",
            kategorie=kat_val, search=search_q if search_q else None,
        )
        total = result.get("total", 0)
        total_pages = result.get("pages", 1)
        leads = [l for l in result.get("items", []) if l.get("email")]
    except Exception:
        leads = []
        total = 0
        total_pages = 1

    if page > total_pages:
        st.session_state["outreach_page"] = 1
        page = 1

    pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
    with pc1:
        if st.button("< Zurueck", disabled=(page <= 1), key="out_prev"):
            st.session_state["outreach_page"] = page - 1
            st.rerun()
    with pc2:
        st.markdown(
            f'<div style="text-align:center;padding-top:6px;color:#b8bec6;font-size:0.85rem;">'
            f'Seite {page} / {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with pc3:
        st.markdown(
            f'<div style="text-align:center;padding-top:6px;color:#e8eaed;font-size:0.85rem;">'
            f'<b>{total}</b> Leads gefunden</div>',
            unsafe_allow_html=True,
        )
    with pc4:
        if st.button("Weiter >", disabled=(page >= total_pages), key="out_next"):
            st.session_state["outreach_page"] = page + 1
            st.rerun()
    with pc5:
        jump = st.number_input("Seite", min_value=1, max_value=total_pages, value=page, key="out_jump", label_visibility="collapsed")
        if jump != page:
            st.session_state["outreach_page"] = jump
            st.rerun()

    if not leads:
        st.info("Keine Leads mit E-Mail auf dieser Seite. Suche anpassen oder Seite wechseln.")
        return

    selected = st.selectbox(
        "Lead auswaehlen",
        range(len(leads)),
        format_func=lambda i: (
            f"{leads[i]['firma']} | "
            f"{leads[i].get('stadt') or '-'} | "
            f"{leads[i]['email']} | "
            f"Ranking: {leads[i].get('ranking_grade') or '?'}"
        ),
        key="outreach_lead_sel",
    )

    sel_lead = leads[selected]
    sent_count = sel_lead.get("email_count", 0)
    email_type = detect_email_type(sent_count)
    type_label = EMAIL_TYPE_LABELS[email_type]
    type_color = EMAIL_TYPE_COLORS[email_type]
    product = get_recommended_product(sel_lead.get("kategorie", "anwalt"))

    oc1, oc2 = st.columns([2, 1])
    with oc1:
        st.markdown(
            f'<span style="background:{type_color}35;color:{type_color};'
            f'border:1px solid {type_color}55;padding:4px 12px;border-radius:12px;'
            f'font-weight:600;font-size:0.85rem;">{type_label}</span>'
            f'&nbsp; <span style="color:#b8bec6;font-size:0.85rem;">'
            f'{sent_count} Mail(s) gesendet · Produkt: {product["name"]}</span>',
            unsafe_allow_html=True,
        )
    with oc2:
        submitted = st.button("✉️ Mail erstellen", type="primary", key="outreach_gen_btn")

    if submitted:
        with st.spinner("KI generiert E-Mail..."):
            try:
                result = api_client.generate_email(sel_lead["id"], email_type)
                if result.get("betreff"):
                    st.session_state["outreach_generated"] = {
                        "lead_id": sel_lead["id"],
                        "lead_firma": sel_lead["firma"],
                        "lead_email": sel_lead["email"],
                        "betreff": result["betreff"],
                        "inhalt": result.get("inhalt", ""),
                    }
                elif result.get("raw"):
                    st.warning("LLM-Antwort konnte nicht als JSON erkannt werden.")
                    st.text(result["raw"])
            except Exception as e:
                st.error(f"Fehler: {e}")

    if "outreach_generated" in st.session_state:
        gen = st.session_state["outreach_generated"]
        st.write("### Generierte E-Mail")
        st.write(f"**An:** {gen['lead_email']}")

        betreff = st.text_input("Betreff", value=gen["betreff"], key="out_betreff")
        inhalt = st.text_area("Inhalt", value=gen["inhalt"], height=300, key="out_inhalt")

        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            if st.button("💾 Als Template speichern"):
                try:
                    api_client.create_custom_template(
                        name=f"Outreach - {gen['lead_firma']}",
                        betreff=betreff,
                        inhalt=inhalt,
                    )
                    st.success("Template gespeichert!")
                except Exception as e:
                    st.error(str(e))

        with bc2:
            if st.button("📤 Direkt senden", type="primary"):
                st.session_state["agent_send_confirm"] = {
                    "lead_id": gen["lead_id"],
                    "lead_firma": gen.get("lead_firma", "?"),
                    "lead_email": gen["lead_email"],
                    "betreff": betreff,
                    "inhalt": inhalt,
                }

        with bc3:
            if st.button("📋 In E-Mail-Modul übernehmen"):
                st.session_state["outreach_draft"] = {
                    "lead_id": gen["lead_id"],
                    "betreff": betreff,
                    "inhalt": inhalt,
                }
                del st.session_state["outreach_generated"]
                st.success("Entwurf gespeichert! Wechseln Sie zur E-Mail-Seite.")

    try:
        smtp_cfg = cached_smtp_config()
        default_test = smtp_cfg.get("from_email", "")
    except Exception:
        default_test = ""

    action, test_addr = render_send_confirm("agent_send_confirm", default_test_email=default_test)
    if action == "send":
        confirm = st.session_state["agent_send_confirm"]
        try:
            api_client.send_email(
                lead_id=confirm["lead_id"],
                subject=confirm["betreff"],
                body=confirm["inhalt"],
            )
            st.success(f"E-Mail gesendet an {confirm['lead_email']}!")
            st.session_state.pop("outreach_generated", None)
        except api_client.APIError as e:
            st.error(f"Fehler: {e.detail}")
        except Exception as e:
            st.error(f"Fehler: {e}")
        del st.session_state["agent_send_confirm"]
    elif action == "test":
        st.info("Test-Mails: Bitte direkt senden und Betreff mit [TEST] markieren.")


def _render_auto_research():
    st.subheader("Auto-Research Agent")
    st.write("Analysieren Sie die Website-Sicherheit Ihrer Leads automatisch.")

    try:
        result = api_client.get_leads(page=1, per_page=200, sort="firma_asc")
        all_leads = result.get("items", [])
    except Exception:
        all_leads = []

    research_leads = [l for l in all_leads if l.get("website")]

    if not research_leads:
        st.warning("Keine Leads mit Website vorhanden.")
        return

    mode = st.radio("Modus", ["Einzeln", "Batch"], horizontal=True, key="research_mode")

    if mode == "Einzeln":
        r_sel = st.selectbox(
            "Lead auswählen",
            range(len(research_leads)),
            format_func=lambda i: f"{research_leads[i]['firma']} — {research_leads[i].get('website', '?')} (Grade: {research_leads[i].get('ranking_grade') or '?'})",
            key="research_sel",
        )

        if st.button("🔬 Analysieren", type="primary", key="research_go"):
            lead = research_leads[r_sel]

            with st.spinner("Prüfe Security Headers..."):
                try:
                    api_client.check_lead_ranking(lead["id"])
                except Exception:
                    pass

            with st.spinner("KI-Analyse läuft..."):
                llm_service = get_llm_service()

                refreshed = api_client.get_lead(lead["id"])

                analysis = llm_service.analyze_lead(
                    firma=refreshed.get("firma", ""),
                    url=refreshed.get("website", ""),
                    grade=refreshed.get("ranking_grade"),
                    score=refreshed.get("ranking_score"),
                    headers=refreshed.get("ranking_details"),
                )

                if analysis.get("success"):
                    content = analysis.get("content", "")
                    try:
                        data = parse_llm_json(content, expect_array=False)
                        st.session_state["research_result"] = {
                            "lead_id": lead["id"],
                            "firma": lead["firma"],
                            "data": data,
                        }
                    except (json.JSONDecodeError, ValueError):
                        st.warning("Analyse konnte nicht als JSON erkannt werden.")
                        st.text(content)
                else:
                    st.error(f"Fehler: {analysis.get('error')}")

        if "research_result" in st.session_state:
            res = st.session_state["research_result"]
            data = res["data"]
            st.write(f"### Analyse: {res['firma']}")

            risiko = data.get("risiko", "?")
            risk_colors = {"Hoch": "#e74c3c", "Mittel": "#f39c12", "Niedrig": "#2ecc71"}
            rc = risk_colors.get(risiko, "#b8bec6")
            st.markdown(
                f'<span style="background:{rc}35;color:{rc};border:1px solid {rc}55;'
                f'padding:4px 12px;border-radius:12px;font-weight:600;">'
                f'Risiko: {risiko}</span>',
                unsafe_allow_html=True,
            )

            st.write("**Zusammenfassung:**")
            st.write(data.get("zusammenfassung", "-"))

            schwachstellen = data.get("schwachstellen", [])
            if schwachstellen:
                st.write("**Schwachstellen:**")
                for s in schwachstellen:
                    st.markdown(f"- {s}")

            empfehlungen = data.get("empfehlungen", [])
            if empfehlungen:
                st.write("**Empfehlungen:**")
                for e in empfehlungen:
                    st.markdown(f"- {e}")

            if st.button("💾 Als Notiz speichern", key="save_research"):
                note_text = (
                    f"[Auto-Research {datetime.utcnow().strftime('%d.%m.%Y')}]\n"
                    f"Risiko: {risiko}\n"
                    f"{data.get('zusammenfassung', '')}\n"
                    f"Schwachstellen: {', '.join(schwachstellen)}\n"
                    f"Empfehlungen: {', '.join(empfehlungen)}"
                )
                try:
                    current = api_client.get_lead(res["lead_id"])
                    existing = current.get("notes") or ""
                    api_client.update_lead(res["lead_id"], notes=(existing + "\n\n" + note_text).strip())
                    st.success("Analyse als Notiz gespeichert!")
                    del st.session_state["research_result"]
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    else:
        unresearched = [l for l in research_leads if not l.get("ranking_grade")]
        st.caption(f"{len(unresearched)} Leads ohne Ranking, {len(research_leads)} total mit Website.")

        max_batch = st.slider("Max. Leads", 1, min(50, len(research_leads)), 10, key="batch_max")
        batch_leads = unresearched[:max_batch] if unresearched else research_leads[:max_batch]

        if st.button(f"🔬 {len(batch_leads)} Leads analysieren", type="primary", key="batch_research"):
            llm_service = get_llm_service()
            progress = st.progress(0)
            status_text = st.empty()

            for i, lead in enumerate(batch_leads):
                status_text.text(f"Analysiere {lead['firma']}... ({i+1}/{len(batch_leads)})")

                try:
                    api_client.check_lead_ranking(lead["id"])
                except Exception:
                    pass

                try:
                    refreshed = api_client.get_lead(lead["id"])
                    analysis = llm_service.analyze_lead(
                        firma=refreshed.get("firma", ""),
                        url=refreshed.get("website", ""),
                        grade=refreshed.get("ranking_grade"),
                        score=refreshed.get("ranking_score"),
                        headers=refreshed.get("ranking_details"),
                    )
                    if analysis.get("success"):
                        try:
                            data = parse_llm_json(analysis["content"], expect_array=False)
                            note = (
                                f"[Auto-Research {datetime.utcnow().strftime('%d.%m.%Y')}] "
                                f"Risiko: {data.get('risiko','?')} | "
                                f"{data.get('zusammenfassung','')}"
                            )
                            existing = refreshed.get("notes") or ""
                            api_client.update_lead(lead["id"], notes=(existing + "\n\n" + note).strip())
                        except (json.JSONDecodeError, ValueError):
                            pass
                except Exception:
                    pass

                progress.progress((i + 1) / len(batch_leads))

            status_text.text("Fertig!")
            st.success(f"{len(batch_leads)} Leads analysiert!")


def _render_search_results(leads_data: list, llm_service):
    scores = [ld.get("fit_score", 0) for ld in leads_data]
    valid_scores = [s for s in scores if isinstance(s, (int, float))]
    high = sum(1 for s in valid_scores if s >= 8)
    medium = sum(1 for s in valid_scores if 5 <= s < 8)
    avg = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0

    st.markdown("---")
    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Gefunden", len(leads_data))
    mc2.metric("Top-Leads (8+)", high)
    mc3.metric("Mittel (5-7)", medium)
    mc4.metric("Ø Fit-Score", avg)

    for idx, ld in enumerate(leads_data):
        firma = ld.get("firma", "Unbekannt")
        score = ld.get("fit_score", 0)
        if not isinstance(score, (int, float)):
            score = 0
        tier = _score_tier(int(score))
        color = SCORE_COLORS[tier]
        stadt_val = ld.get("stadt", "")
        branche_val = ld.get("branche", "")
        website_val = ld.get("website", "")

        header = f"{firma} — {stadt_val}"
        if branche_val:
            header += f" · {branche_val}"

        with st.expander(f"**{header}**  |  Score: {score}/10", expanded=(idx < 3)):
            sc1, sc2 = st.columns([1, 4])
            with sc1:
                st.markdown(
                    f'<div style="text-align:center;padding:8px 0;">'
                    f'<div style="font-size:2rem;font-weight:700;color:{color};'
                    f'font-family:JetBrains Mono,monospace;">{score}</div>'
                    f'<div style="font-size:0.78rem;color:#b8bec6;text-transform:uppercase;">Fit-Score</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with sc2:
                if website_val:
                    url = website_val if website_val.startswith("http") else f"https://{website_val}"
                    st.markdown(f"**Website:** [{website_val}]({url})")
                groesse_val = ld.get("groesse", "")
                if groesse_val:
                    st.caption(f"Grösse: {groesse_val}")

            fit_grund = ld.get("fit_grund", "")
            if fit_grund:
                st.markdown(f"**Warum passend:** {fit_grund}")

            dc1, dc2 = st.columns(2)
            with dc1:
                entscheider = ld.get("entscheider", "")
                if entscheider:
                    st.markdown(f"**Entscheider:** {entscheider}")
                kontakt = ld.get("kontakt_strategie", "")
                if kontakt:
                    st.markdown(f"**Kontakt-Strategie:** {kontakt}")
            with dc2:
                wert = ld.get("wertversprechen", "")
                if wert:
                    st.markdown(f"**Wertversprechen:** {wert}")
                einstieg = ld.get("gespraechseinstieg", [])
                if einstieg:
                    st.markdown("**Gesprächseinstieg:**")
                    for punkt in (einstieg if isinstance(einstieg, list) else [einstieg]):
                        st.markdown(f"- {punkt}")

            bemerkung = ld.get("bemerkung", "")
            if bemerkung:
                st.caption(f"Bemerkung: {bemerkung}")

    st.markdown("---")
    ac1, ac2, ac3 = st.columns(3)

    save_kat = ac1.selectbox("Kategorie", ALL_KATEGORIEN, key="save_kategorie")

    with ac2:
        if st.button("💾 Alle speichern", type="primary"):
            _save_leads_via_api(leads_data, save_kat)
            del st.session_state["search_results"]
            st.rerun()

        if high > 0 and st.button("⭐ Nur Top-Leads (8+) speichern"):
            top = [ld for ld in leads_data if isinstance(ld.get("fit_score", 0), (int, float)) and ld["fit_score"] >= 8]
            _save_leads_via_api(top, save_kat)
            del st.session_state["search_results"]
            st.rerun()

    with ac3:
        csv_data = _leads_to_csv(leads_data)
        st.download_button(
            "📥 CSV Export",
            data=csv_data,
            file_name=f"lead_recherche_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

        if st.button("🗑️ Ergebnisse löschen"):
            del st.session_state["search_results"]
            st.rerun()


def _save_leads_via_api(leads_data: list, kategorie: str):
    count = 0
    for ld in leads_data:
        firma = str(ld.get("firma", "")).strip()
        if not firma:
            continue

        note_parts = []
        fit_score = ld.get("fit_score")
        if fit_score:
            note_parts.append(f"Fit-Score: {fit_score}/10")
        for key, label in [("fit_grund", "Warum passend"), ("entscheider", "Entscheider"),
                           ("kontakt_strategie", "Kontakt-Strategie"), ("wertversprechen", "Wertversprechen")]:
            val = ld.get(key, "")
            if val:
                note_parts.append(f"{label}: {val}")
        einstieg = ld.get("gespraechseinstieg", [])
        if einstieg:
            if isinstance(einstieg, list):
                einstieg = ", ".join(einstieg)
            note_parts.append(f"Gesprächseinstieg: {einstieg}")
        bemerkung = ld.get("bemerkung", "")
        if bemerkung:
            note_parts.append(f"Bemerkung: {bemerkung}")

        notes = ""
        if note_parts:
            notes = f"[Lead-Recherche {datetime.utcnow().strftime('%d.%m.%Y')}]\n" + "\n".join(note_parts)

        try:
            api_client.create_lead(
                firma=firma,
                stadt=ld.get("stadt", ""),
                website=ld.get("website", ""),
                kategorie=kategorie,
                quelle="llm_search",
                notes=notes,
            )
            count += 1
        except Exception:
            pass

    st.success(f"{count} Leads gespeichert!")


def _leads_to_csv(leads_data: list) -> str:
    rows = []
    for ld in leads_data:
        einstieg = ld.get("gespraechseinstieg", [])
        if isinstance(einstieg, list):
            einstieg = " | ".join(einstieg)
        rows.append({
            "Firma": ld.get("firma", ""),
            "Website": ld.get("website", ""),
            "Stadt": ld.get("stadt", ""),
            "Branche": ld.get("branche", ""),
            "Grösse": ld.get("groesse", ""),
            "Fit-Score": ld.get("fit_score", ""),
            "Warum passend": ld.get("fit_grund", ""),
            "Entscheider": ld.get("entscheider", ""),
            "Kontakt-Strategie": ld.get("kontakt_strategie", ""),
            "Wertversprechen": ld.get("wertversprechen", ""),
            "Gesprächseinstieg": einstieg,
            "Bemerkung": ld.get("bemerkung", ""),
        })
    df = pd.DataFrame(rows)
    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=";", encoding="utf-8")
    return buf.getvalue()
