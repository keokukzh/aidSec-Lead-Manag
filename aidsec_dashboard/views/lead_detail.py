"""Lead Detail - 360-Grad Lead-Ansicht — powered by API"""
import streamlit as st
from datetime import datetime, date
import api_client
from cache_helpers import cached_smtp_config, cached_email_signature, cached_templates
from services.outreach import (
    detect_email_type,
    get_recommended_product,
    EMAIL_TYPE_LABELS,
    EMAIL_TYPE_COLORS,
)
from views.email import render_send_confirm

ALL_STATUSES = ["offen", "pending", "gewonnen", "verloren"]
ALL_CATEGORIES = ["anwalt", "praxis", "wordpress"]
ALL_CATEGORIES_DISPLAY = {"anwalt": "Anwalt", "praxis": "Praxis", "wordpress": "WordPress"}


def render(lead_id: int):
    cache_key = f"_lead_cache_{lead_id}"
    if st.session_state.get("_lead_refresh"):
        st.session_state.pop(cache_key, None)
        st.session_state.pop("_lead_refresh", None)
    try:
        lead = st.session_state.get(cache_key)
        if not lead:
            lead = api_client.get_lead(lead_id)
            st.session_state[cache_key] = lead
    except Exception:
        st.error("Lead nicht gefunden.")
        if st.button("← Zurück"):
            st.session_state.pop("selected_lead_id", None)
            st.rerun()
        return

    _render_header(lead)

    flash = st.session_state.pop("ld_rank_flash", None)
    if flash:
        if flash["type"] == "success":
            g = flash["grade"]
            st.success(
                f"✅ Ranking gespeichert — Grade **{g}** · "
                f"{flash['score']}/100 Punkte"
            )
        else:
            st.error(f"❌ Ranking-Fehler: {flash.get('msg', 'Unbekannt')}")

    _render_quick_actions(lead)
    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Übersicht", "📅 Kontakt-Timeline", "✉️ E-Mail", "🔍 Ranking",
    ])

    with tab1:
        _render_overview(lead)
    with tab2:
        _render_timeline(lead)
    with tab3:
        _render_email_tab(lead)
    with tab4:
        _render_ranking_tab(lead)


def _render_header(lead):
    hc1, hc2 = st.columns([0.6, 5])
    with hc1:
        if st.button("← Zurück", key="ld_back"):
            st.session_state.pop("selected_lead_id", None)
            st.rerun()
    with hc2:
        sv = lead.get("status", "offen")
        firma = lead.get("firma", "?")
        website = lead.get("website") or "-"
        email = lead.get("email") or "-"
        stadt = lead.get("stadt") or "-"
        kategorie = lead.get("kategorie", "-")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;">'
            f'<span style="font-size:1.5rem;font-weight:700;">{firma}</span>'
            f'<span class="status-badge badge-{sv}">{sv}</span>'
            f'</div>'
            f'<div style="color:#b8bec6;font-size:0.85rem;margin-top:4px;">'
            f'{website} &nbsp;|&nbsp; {email} &nbsp;|&nbsp; '
            f'{stadt} &nbsp;|&nbsp; {kategorie}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_quick_actions(lead):
    lead_id = lead["id"]
    ac1, ac2, ac3, ac4 = st.columns(4)

    with ac1:
        current_status = lead.get("status", "offen")
        idx = ALL_STATUSES.index(current_status) if current_status in ALL_STATUSES else 0
        new_status = st.selectbox(
            "Status ändern",
            ALL_STATUSES,
            index=idx,
            key="ld_status",
        )
        if new_status != current_status:
            try:
                api_client.update_lead(lead_id, status=new_status)
                st.session_state["_lead_refresh"] = True
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with ac2:
        if st.button("🔍 Ranking prüfen", key="ld_rank_check"):
            if lead.get("website"):
                with st.spinner("Prüfe Security Headers..."):
                    try:
                        result = api_client.check_lead_ranking(lead_id)
                        if result.get("grade"):
                            st.session_state["ld_rank_flash"] = {
                                "type": "success",
                                "grade": result["grade"],
                                "score": result.get("score", 0),
                            }
                        else:
                            st.session_state["ld_rank_flash"] = {
                                "type": "error",
                                "msg": result.get("error", "Kein Ergebnis erhalten"),
                            }
                    except Exception as e:
                        st.session_state["ld_rank_flash"] = {
                            "type": "error", "msg": str(e),
                        }
                st.session_state["_lead_refresh"] = True
                st.rerun()
            else:
                st.warning("Keine Website hinterlegt.")

    with ac3:
        if st.button("📝 Notiz bearbeiten", key="ld_note_toggle"):
            st.session_state["ld_show_note"] = not st.session_state.get("ld_show_note", False)

    with ac4:
        if st.button("📅 Follow-up planen", key="ld_fu_toggle"):
            st.session_state["ld_show_followup"] = not st.session_state.get("ld_show_followup", False)

    if st.session_state.get("ld_show_note"):
        notes = st.text_area("Notizen", value=lead.get("notes") or "", height=100, key="ld_inline_notes")
        if st.button("💾 Speichern", key="ld_save_inline_note"):
            try:
                api_client.update_lead(lead["id"], notes=notes)
                st.session_state["ld_show_note"] = False
                st.session_state["_lead_refresh"] = True
                st.success("Notiz gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    if st.session_state.get("ld_show_followup"):
        _render_followup_form(lead)


def _render_followup_form(lead):
    fc1, fc2 = st.columns([1, 2])
    with fc1:
        fu_date = st.date_input("Datum", key="ld_fu_date")
    with fc2:
        fu_note = st.text_input("Notiz", placeholder="Rückruf vereinbart...", key="ld_fu_note")
    if st.button("💾 Follow-up speichern", key="ld_fu_save"):
        try:
            datum_str = datetime.combine(fu_date, datetime.min.time()).isoformat()
            api_client.create_followup(lead["id"], datum=datum_str, notiz=fu_note)
            st.session_state["ld_show_followup"] = False
            st.success("Follow-up geplant!")
            st.rerun()
        except Exception as e:
            st.error(str(e))


def _render_overview(lead):
    lead_id = lead["id"]

    # Toggle button for edit mode
    if "ld_edit_mode" not in st.session_state:
        st.session_state["ld_edit_mode"] = False

    edit_btn_label = "✏️ Bearbeiten" if not st.session_state["ld_edit_mode"] else "❌ Abbrechen"
    if st.button(edit_btn_label, key="ld_toggle_edit"):
        st.session_state["ld_edit_mode"] = not st.session_state["ld_edit_mode"]
        st.rerun()

    if st.session_state["ld_edit_mode"]:
        # Render edit form
        with st.form("ld_edit_form"):
            st.markdown("#### Lead-Daten bearbeiten")

            ec1, ec2 = st.columns(2)
            with ec1:
                firma = st.text_input("Firma", value=lead.get("firma") or "")
                website = st.text_input("Website", value=lead.get("website") or "")
                email = st.text_input("E-Mail", value=lead.get("email") or "")
                telefon = st.text_input("Telefon", value=lead.get("telefon") or "")
            with ec2:
                stadt = st.text_input("Stadt", value=lead.get("stadt") or "")
                # Get current category (ensure lowercase)
                current_cat = lead.get("kategorie", "anwalt").lower() if lead.get("kategorie") else "anwalt"
                # Create options with format (value, label)
                cat_options = [(k, v) for k, v in ALL_CATEGORIES_DISPLAY.items()]
                cat_index = next((i for i, (k, v) in enumerate(cat_options) if k == current_cat), 0)
                selected_cat = st.selectbox(
                    "Kategorie",
                    options=cat_options,
                    format_func=lambda x: x[1],
                    index=cat_index,
                    key="ld_kategorie"
                )
                kategorie = selected_cat[0]  # Get the lowercase value
                quelle = st.text_input("Quelle", value=lead.get("quelle") or "")
                wordpress_detected = st.checkbox(
                    "WordPress erkannt",
                    value=bool(lead.get("wordpress_detected") == "true" or lead.get("wordpress_detected") == True)
                )

            save_btn = st.form_submit_button("💾 Änderungen speichern", type="primary")

        if save_btn:
            # Validate email format
            if email and "@" not in email:
                st.error("Ungültige E-Mail-Adresse")
                return
            try:
                api_client.update_lead(
                    lead_id,
                    firma=firma,
                    website=website,
                    email=email,
                    telefon=telefon,
                    stadt=stadt,
                    kategorie=kategorie,
                    quelle=quelle,
                    wordpress_detected="true" if wordpress_detected else "false"
                )
                st.session_state["ld_edit_mode"] = False
                st.session_state["_lead_refresh"] = True
                st.success("Lead gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(f"Fehler beim Speichern: {e}")
    else:
        # Display mode
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Firma:** {lead.get('firma', '-')}")
            st.markdown(f"**Website:** `{lead.get('website') or '-'}`")
            st.markdown(f"**E-Mail:** {lead.get('email') or '-'}")
            st.markdown(f"**Telefon:** {lead.get('telefon') or '-'}")
        with c2:
            st.markdown(f"**Stadt:** {lead.get('stadt') or '-'}")
            cat = lead.get('kategorie', 'anwalt').lower() if lead.get('kategorie') else 'anwalt'
            cat_display = ALL_CATEGORIES_DISPLAY.get(cat, cat)
            st.markdown(f"**Kategorie:** {cat_display}")
            st.markdown(f"**Quelle:** {lead.get('quelle') or '-'}")
            wp = lead.get("wordpress_detected")
            if wp == "true" or wp == True:
                st.markdown("**WordPress:** ✅ erkannt")

    st.markdown("---")

    # Ranking info (always visible)
    grade = lead.get("ranking_grade") or "-"
    if grade in "ABCDF":
        grade_html = f'<span class="grade-badge grade-{grade}">{grade}</span>'
    else:
        grade_html = grade

    created = lead.get("created_at")
    if created:
        if isinstance(created, str):
            try:
                created = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except Exception:
                pass
        if isinstance(created, datetime):
            created = created.strftime("%d.%m.%Y")

    checked_at = lead.get("ranking_checked_at")
    if checked_at:
        if isinstance(checked_at, str):
            try:
                checked_at = datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
            except Exception:
                pass
        if isinstance(checked_at, datetime):
            checked_at = checked_at.strftime("%d.%m.%Y %H:%M")

    st.markdown(f"**Ranking:** {grade_html} ({lead.get('ranking_score') or '-'})")
    st.markdown(f"**Erstellt:** {created or '-'}")
    if checked_at:
        st.markdown(f"**Letzter Check:** {checked_at}")

    st.markdown("---")
    notes = st.text_area("Notizen", value=lead.get("notes") or "", height=120, key="ld_notes")
    if st.button("💾 Notizen speichern", key="ld_save_notes"):
        try:
            api_client.update_lead(lead["id"], notes=notes)
            st.success("Gespeichert!")
        except Exception as e:
            st.error(str(e))

    try:
        followups = api_client.get_followups(lead_id=lead["id"])
        open_fus = [f for f in followups if not f.get("erledigt")]
        if open_fus:
            st.markdown("---")
            st.write("#### Geplante Follow-ups")
            for fu in sorted(open_fus, key=lambda f: f.get("datum", "")):
                icon = "✅" if fu.get("erledigt") else "📅"
                d = fu.get("datum", "-")
                if isinstance(d, str) and "T" in d:
                    d = d.split("T")[0]
                    parts = d.split("-")
                    if len(parts) == 3:
                        d = f"{parts[2]}.{parts[1]}.{parts[0]}"
                st.markdown(f"{icon} **{d}** — {fu.get('notiz') or '-'}")
    except Exception:
        pass


@st.fragment
def _render_timeline(lead):
    try:
        events = api_client.get_lead_timeline(lead["id"])
    except Exception:
        st.info("Timeline konnte nicht geladen werden.")
        return

    if not events:
        st.info("Noch keine Aktivitäten für diesen Lead.")
        return

    type_colors = {"status": "#3498db", "email": "#00d4aa", "followup": "#f0a500"}
    type_icons = {
        "status": "🔄",
        "email_sent": "✅",
        "email_failed": "❌",
        "email_draft": "📝",
        "followup_done": "✅",
        "followup_pending": "📅",
    }

    for ev in events:
        d = "-"
        if ev.get("date"):
            try:
                dt = datetime.fromisoformat(ev["date"].replace("Z", "+00:00"))
                d = dt.strftime("%d.%m.%Y %H:%M")
            except Exception:
                d = ev["date"]

        ev_type = ev.get("type", "status")
        color = type_colors.get(ev_type, "#b8bec6")

        if ev_type == "email":
            status = ev.get("status", "sent")
            icon = type_icons.get(f"email_{status}", "📧")
        elif ev_type == "followup":
            done = ev.get("done", False)
            icon = type_icons.get(f"followup_{'done' if done else 'pending'}", "📅")
        else:
            icon = type_icons.get(ev_type, "🔄")

        detail = ev.get("detail", "")
        st.markdown(
            f'<div style="display:flex;align-items:flex-start;gap:12px;'
            f'padding:8px 0;border-bottom:1px solid #2a304044;">'
            f'<div style="font-size:1.1rem;">{icon}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-weight:600;font-size:0.8rem;text-transform:uppercase;'
            f'letter-spacing:0.05em;color:{color};">{ev_type}</div>'
            f'<div style="color:#e8eaed;">{detail}</div>'
            f'</div>'
            f'<div style="color:#b8bec6;font-size:0.85rem;'
            f'font-family:JetBrains Mono,monospace;white-space:nowrap;">{d}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_email_tab(lead):
    lead_id = lead["id"]

    try:
        smtp_cfg = cached_smtp_config()
        if not smtp_cfg.get("configured"):
            st.warning("SMTP nicht konfiguriert. Bitte unter Einstellungen einrichten.")
            return
    except Exception:
        st.warning("SMTP-Status konnte nicht geprüft werden.")
        return

    if not lead.get("email"):
        st.warning("Keine E-Mail-Adresse hinterlegt.")
        return

    sig_data = {"text": cached_email_signature()}

    try:
        templates_raw = cached_templates()
        choices = {"Eigene E-Mail": None}
        for t in templates_raw:
            choices[f"[Standard] {t['name']}"] = {"betreff": t["betreff"], "inhalt": t["inhalt"]}
    except Exception:
        choices = {"Eigene E-Mail": None}

    sent_count = lead.get("email_count", 0)
    email_type = detect_email_type(sent_count)
    type_label = EMAIL_TYPE_LABELS[email_type]
    type_color = EMAIL_TYPE_COLORS[email_type]

    rec_product = get_recommended_product(lead.get("kategorie", "anwalt"))

    variables = {
        "firma": lead.get("firma", ""),
        "stadt": lead.get("stadt") or "Schweiz",
        "website": lead.get("website") or "",
        "ranking_grade": lead.get("ranking_grade") or "?",
        "ranking_score": str(lead.get("ranking_score") or "?"),
        "absender_name": smtp_cfg.get("from_name", ""),
        "produkt": rec_product.get("name", "Rapid Header Fix"),
        "preis": rec_product.get("preis", "CHF 490.–"),
    }

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Gesendet", sent_count)
    mc2.metric("E-Mail Typ", type_label)
    with mc3:
        st.markdown(
            f'<div style="margin-top:12px;">'
            f'<span style="background:{type_color}35;color:{type_color};'
            f'border:1px solid {type_color}55;padding:4px 12px;border-radius:12px;'
            f'font-weight:600;font-size:0.85rem;">{type_label}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    ki_btn = st.button("🤖 KI Mail erstellen", key="ld_ki_gen", type="primary")

    if ki_btn:
        with st.spinner("KI generiert E-Mail..."):
            try:
                result = api_client.generate_email(lead_id, email_type)
                if result.get("betreff"):
                    st.session_state["ld_ki_draft"] = {
                        "betreff": result["betreff"],
                        "inhalt": result.get("inhalt", ""),
                    }
                elif result.get("raw"):
                    st.warning("KI-Antwort konnte nicht verarbeitet werden.")
                    st.text(result["raw"])
            except api_client.APIError as e:
                st.error(f"Fehler: {e.detail}")
            except Exception as e:
                st.error(f"Fehler: {e}")

    ki_draft = st.session_state.get("ld_ki_draft")

    with st.form("ld_email_form"):
        template_name = st.selectbox("Template", list(choices.keys()), key="ld_tpl")
        tpl = choices[template_name]

        if ki_draft:
            betreff = ki_draft["betreff"]
            inhalt = ki_draft["inhalt"]
        elif tpl:
            betreff = tpl["betreff"]
            inhalt = tpl["inhalt"]
        else:
            betreff = ""
            inhalt = ""

        for k, v in variables.items():
            betreff = betreff.replace(f"{{{k}}}", str(v))
            inhalt = inhalt.replace(f"{{{k}}}", str(v))

        betreff_input = st.text_input("Betreff", value=betreff, key="ld_betreff")
        inhalt_input = st.text_area("Inhalt", value=inhalt, height=250, key="ld_inhalt")

        append_sig = False
        if sig_data.get("text"):
            append_sig = st.checkbox("✍️ Signatur anfügen", value=True, key="ld_sig")

        send_btn = st.form_submit_button("📤 Senden", type="primary")

    final_body = inhalt_input
    if append_sig and sig_data.get("text"):
        final_body = inhalt_input + "\n\n-- \n" + sig_data["text"]

    if send_btn:
        st.session_state["ld_email_confirm"] = {
            "lead_id": lead_id,
            "lead_firma": lead.get("firma", ""),
            "lead_email": lead.get("email", ""),
            "betreff": betreff_input,
            "inhalt": final_body,
        }

    action, test_addr = render_send_confirm("ld_email_confirm", default_test_email=smtp_cfg.get("from_email", ""))
    if action == "send":
        confirm = st.session_state["ld_email_confirm"]
        with st.spinner("Sende E-Mail..."):
            try:
                api_client.send_email(
                    lead_id=confirm["lead_id"],
                    subject=confirm["betreff"],
                    body=confirm["inhalt"],
                )
                st.success(f"✅ E-Mail gesendet an {confirm['lead_email']}!")
            except api_client.APIError as e:
                st.error(f"❌ Fehler: {e.detail}")
            except Exception as e:
                st.error(f"❌ Fehler: {e}")
        del st.session_state["ld_email_confirm"]
        st.session_state.pop("ld_ki_draft", None)
    elif action == "test":
        confirm = st.session_state["ld_email_confirm"]
        st.info("Test-Mails werden über die API noch nicht unterstützt.")

    try:
        history = api_client.get_email_history(lead_id)
        if history:
            st.markdown("---")
            st.write("#### E-Mail Verlauf")
            for eh in history:
                status_label = "Gesendet" if eh.get("status") == "sent" else "Fehler" if eh.get("status") == "failed" else "Entwurf"
                d = eh.get("gesendet_at", "-")
                if isinstance(d, str) and "T" in d:
                    try:
                        dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
                        d = dt.strftime("%d.%m.%Y %H:%M")
                    except Exception:
                        pass
                with st.expander(f"{status_label} -- {d} -- {eh.get('betreff', '')}"):
                    st.text(eh.get("inhalt", ""))
    except Exception:
        pass


def _render_ranking_tab(lead):
    lead_id = lead["id"]

    if lead.get("ranking_grade"):
        grade = lead["ranking_grade"]
        score = lead.get("ranking_score") or 0

        gc1, gc2, gc3 = st.columns(3)
        with gc1:
            st.markdown(
                f'<div style="text-align:center;">'
                f'<span class="grade-badge grade-{grade}" '
                f'style="width:64px;height:64px;line-height:64px;font-size:2rem;">'
                f'{grade}</span></div>',
                unsafe_allow_html=True,
            )
        gc2.metric("Score", f"{score}/100")
        checked_at = lead.get("ranking_checked_at")
        if checked_at and isinstance(checked_at, str):
            try:
                checked_at = datetime.fromisoformat(checked_at.replace("Z", "+00:00")).strftime("%d.%m.%Y")
            except Exception:
                pass
        gc3.metric("Geprüft am", checked_at or "-")

        details = lead.get("ranking_details")
        if details and isinstance(details, list):
            st.markdown("---")
            st.write("#### Header Details")
            for h in details:
                rating = h.get("rating", "good")
                rc = {"good": "#2ecc71", "warning": "#f39c12", "bad": "#e74c3c"}
                color = rc.get(rating, "#b8bec6")
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:4px 0;border-bottom:1px solid #2a304033;">'
                    f'<span style="color:{color};font-weight:500;">{h["name"]}</span>'
                    f'<span style="color:#b8bec6;font-size:0.85rem;">'
                    f'{str(h.get("value",""))[:80]}</span></div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Noch nicht geprüft.")

    st.markdown("---")

    if lead.get("website"):
        if st.button("🔍 Jetzt prüfen", key="ld_check_rank", type="primary"):
            with st.spinner("Prüfe Security Headers..."):
                try:
                    result = api_client.check_lead_ranking(lead_id)
                    if result.get("grade"):
                        st.session_state["ld_rank_flash"] = {
                            "type": "success",
                            "grade": result["grade"],
                            "score": result.get("score", 0),
                        }
                    else:
                        st.session_state["ld_rank_flash"] = {
                            "type": "error",
                            "msg": result.get("error", "Kein Ergebnis erhalten"),
                        }
                except Exception as e:
                    st.session_state["ld_rank_flash"] = {
                        "type": "error", "msg": str(e),
                    }
            st.rerun()
    else:
        st.warning("Keine Website hinterlegt.")
