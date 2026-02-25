"""E-Mail Page - Email Management and Sending — powered by API"""
import streamlit as st
import time
from datetime import datetime
import api_client
from cache_helpers import (
    cached_smtp_config,
    cached_templates,
    cached_custom_templates,
    cached_email_signature,
    cached_daily_email_count,
    invalidate_templates,
    invalidate_email,
)
from services.outreach import (
    detect_email_type,
    get_recommended_product,
    EMAIL_TYPE_LABELS,
    EMAIL_TYPE_COLORS,
)


def render_send_confirm(state_key, default_test_email=""):
    """Render email send confirmation dialog.

    Expects st.session_state[state_key] to be a dict with at least:
      lead_firma, lead_email, betreff, inhalt

    Returns: ('send', None) | ('test', test_email_str) | (None, None)
    """
    data = st.session_state.get(state_key)
    if not data:
        return None, None

    with st.container(border=True):
        st.markdown("#### Senden bestätigen")

        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"**An:** {data['lead_firma']}")
            st.markdown(f"**E-Mail:** `{data['lead_email']}`")
        with c2:
            st.markdown(f"**Betreff:** {data['betreff']}")
            preview = data["inhalt"]
            if len(preview) > 200:
                preview = preview[:200] + "..."
            st.caption(preview)

        st.divider()
        test_email = st.text_input(
            "Test-Adresse",
            value=default_test_email,
            key=f"{state_key}_test_addr",
            placeholder="eigene@email.ch",
        )

        b1, b2, b3 = st.columns(3)
        with b1:
            real = st.button("📤 An Kunde senden", type="primary", key=f"{state_key}_real")
        with b2:
            test = st.button("🧪 Als Test senden", key=f"{state_key}_test")
        with b3:
            cancel = st.button("❌ Abbrechen", key=f"{state_key}_cancel")

    if cancel:
        del st.session_state[state_key]
        st.rerun()
    if real:
        return "send", None
    if test:
        if not test_email or not test_email.strip():
            st.warning("Bitte eine Test-E-Mail-Adresse eingeben.")
            return None, None
        return "test", test_email.strip()
    return None, None


def render():
    """Render email page"""
    st.title("📧 E-Mail Management")

    try:
        smtp_cfg = cached_smtp_config()
    except Exception:
        st.error("API nicht erreichbar.")
        return

    if not smtp_cfg.get("configured"):
        st.warning("⚠️ SMTP nicht konfiguriert!")
        st.info("Bitte konfigurieren Sie SMTP unter **Einstellungen** in der Seitenleiste.")
        return

    draft = st.session_state.get("outreach_draft")
    if draft:
        st.info(f"📝 Entwurf von Outreach Helper: **{draft.get('betreff', '')}**")

    tab1, tab2, tab3 = st.tabs(["✉️ E-Mail senden", "📝 Templates", "📬 Verlauf"])

    with tab1:
        _render_send_tab(smtp_cfg, draft)

    with tab2:
        _render_templates_tab()

    with tab3:
        _render_history_tab()


def _render_send_tab(smtp_cfg, draft):
    st.subheader("E-Mail an Leads senden")

    try:
        daily = cached_daily_email_count()
        today_sent = daily.get("count", 0)
    except Exception:
        today_sent = 0

    tc1, tc2 = st.columns([1, 3])
    with tc1:
        color = "#2ecc71" if today_sent < 10 else "#f39c12" if today_sent < 20 else "#e74c3c"
        st.markdown(
            f'<div style="background:{color}30;border:1px solid {color}55;border-radius:8px;'
            f'padding:8px 14px;text-align:center;">'
            f'<span style="font-size:1.3rem;font-weight:700;color:{color};">{today_sent}</span>'
            f'<span style="color:#b8bec6;font-size:0.85rem;display:block;">Mails heute</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with tc2:
        if today_sent >= 10:
            st.warning(
                "Warm-Up-Phase: Bei neuer Domain max. 10-15 Mails/Tag senden. "
                "Zu viele Mails zu schnell verschlechtern deine Reputation."
            )

    kat_labels = {"Alle": None, "Anwalt": "anwalt", "Praxis": "praxis", "WordPress": "wordpress"}
    status_map = {"offen+pending": "offen,pending", "offen": "offen", "pending": "pending", "Alle": None}

    fc1, fc2, fc3, fc4 = st.columns([3, 1, 1, 1])
    with fc1:
        search_term = st.text_input(
            "Suche",
            placeholder="Firma, E-Mail oder Stadt...",
            key="email_search",
        )
    with fc2:
        kategorie_filter = st.selectbox(
            "Kategorie", list(kat_labels.keys()), key="email_kat_filter"
        )
    with fc3:
        status_filter = st.selectbox(
            "Status", list(status_map.keys()),
            key="email_status_filter",
        )
    with fc4:
        per_page = st.selectbox("Pro Seite", [25, 50, 100], index=1, key="email_pp")

    cur_filter_key = f"{search_term}|{kategorie_filter}|{status_filter}|{per_page}"
    if st.session_state.get("_email_filter_key") != cur_filter_key:
        st.session_state["_email_filter_key"] = cur_filter_key
        st.session_state["email_page"] = 1
    page = st.session_state.get("email_page", 1)

    kat_val = kat_labels.get(kategorie_filter)
    status_val = status_map.get(status_filter)
    search_val = search_term if search_term else None

    try:
        res = api_client.get_leads(
            page=page, per_page=per_page,
            status=status_val, kategorie=kat_val, search=search_val,
        )
        leads = [l for l in res.get("items", []) if l.get("email")]
        total = res.get("total", 0)
        total_pages = res.get("pages", 1)
    except Exception:
        leads = []
        total = 0
        total_pages = 1

    if page > total_pages:
        st.session_state["email_page"] = 1
        page = 1

    pc1, pc2, pc3, pc4 = st.columns([1, 2, 2, 1])
    with pc1:
        if st.button("< Zurueck", disabled=(page <= 1), key="em_prev"):
            st.session_state["email_page"] = page - 1
            st.rerun()
    with pc2:
        st.markdown(
            f'<div style="text-align:center;padding-top:6px;color:#b8bec6;font-size:0.85rem;">'
            f'Seite <b>{page}</b> / {total_pages}</div>',
            unsafe_allow_html=True,
        )
    with pc3:
        st.markdown(
            f'<div style="text-align:center;padding-top:6px;color:#e8eaed;font-size:0.85rem;">'
            f'<b>{total}</b> Leads insgesamt &middot; <b>{len(leads)}</b> auf dieser Seite</div>',
            unsafe_allow_html=True,
        )
    with pc4:
        if st.button("Weiter >", disabled=(page >= total_pages), key="em_next"):
            st.session_state["email_page"] = page + 1
            st.rerun()

    if not leads:
        st.info("Keine Leads gefunden. Filter anpassen oder Seite wechseln.")
        return

    sig_text = cached_email_signature()

    try:
        templates_raw = cached_templates()
        custom_raw = cached_custom_templates()
        template_choices = {"Eigene E-Mail": None}
        for t in templates_raw:
            template_choices[f"[Standard] {t['name']}"] = {"betreff": t["betreff"], "inhalt": t["inhalt"]}
        for t in custom_raw:
            template_choices[f"[Custom] {t['name']}"] = {"betreff": t["betreff"], "inhalt": t["inhalt"]}
    except Exception:
        template_choices = {"Eigene E-Mail": None}

    send_mode = st.radio("Modus", ["Einzeln", "Bulk (mehrere Leads)"], horizontal=True)

    if send_mode == "Einzeln":
        _render_single_send(leads, template_choices, smtp_cfg, draft, sig_text)
    else:
        _render_bulk_send(leads, template_choices, smtp_cfg, sig_text)


def _render_lead_data_check(lead):
    """Show data completeness warnings with quick-fix buttons."""
    has_email = bool(lead.get("email"))
    has_website = bool(lead.get("website"))
    has_ranking = bool(lead.get("ranking_grade"))

    if has_email and has_website and has_ranking:
        grade = lead["ranking_grade"]
        score = lead.get("ranking_score", "?")
        gc = {"A": "#2ecc71", "B": "#f1c40f", "C": "#e67e22", "D": "#e74c3c", "F": "#c0392b"}.get(grade, "#b8bec6")
        st.markdown(
            f'<div style="background:#1a1f2e;border:1px solid #2a3040;border-radius:8px;padding:10px 14px;'
            f'display:flex;gap:16px;align-items:center;flex-wrap:wrap;">'
            f'<span style="color:#2ecc71;font-weight:600;">[OK]</span> {lead["email"]}'
            f'&nbsp;&nbsp;<span style="color:#2ecc71;font-weight:600;">[OK]</span> {lead["website"]}'
            f'&nbsp;&nbsp;<span style="color:{gc};font-weight:700;font-family:JetBrains Mono,monospace;">'
            f'Ranking: {grade} ({score}/100)</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return True

    with st.container(border=True):
        st.markdown(f"**Daten-Check: {lead.get('firma', '?')}**")

        if has_email:
            st.markdown(f"<span style='color:#2ecc71;font-weight:600;'>[OK]</span> E-Mail: {lead['email']}", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#e74c3c;font-weight:600;'>[FEHLT]</span> E-Mail-Adresse fehlt", unsafe_allow_html=True)
            new_email = st.text_input("E-Mail nachtragen", key=f"fix_email_{lead['id']}", placeholder="email@firma.ch")
            if new_email and st.button("Speichern", key=f"save_email_{lead['id']}"):
                try:
                    api_client.update_lead(lead["id"], email=new_email)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if has_website:
            st.markdown(f"<span style='color:#2ecc71;font-weight:600;'>[OK]</span> Website: {lead['website']}", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color:#f39c12;font-weight:600;'>[FEHLT]</span> Website fehlt", unsafe_allow_html=True)
            new_web = st.text_input("Website nachtragen", key=f"fix_web_{lead['id']}", placeholder="www.firma.ch")
            if new_web and st.button("Speichern", key=f"save_web_{lead['id']}"):
                try:
                    api_client.update_lead(lead["id"], website=new_web)
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

        if has_ranking:
            grade = lead["ranking_grade"]
            score = lead.get("ranking_score", "?")
            gc = {"A": "#2ecc71", "B": "#f1c40f", "C": "#e67e22", "D": "#e74c3c", "F": "#c0392b"}.get(grade, "#b8bec6")
            st.markdown(
                f"<span style='color:{gc};font-weight:600;'>[{grade}]</span> "
                f"Ranking: {grade} (Score: {score}/100)",
                unsafe_allow_html=True,
            )
        else:
            st.markdown("<span style='color:#f39c12;font-weight:600;'>[FEHLT]</span> Ranking nicht geprueft", unsafe_allow_html=True)
            if has_website and st.button("Ranking jetzt pruefen", key=f"check_rank_{lead['id']}", type="primary"):
                with st.spinner("Pruefe Security Headers..."):
                    try:
                        api_client.check_lead_ranking(lead["id"])
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            elif not has_website:
                st.caption("Website muss zuerst eingetragen werden.")

    return has_email


def _render_bulk_data_summary(leads_info):
    """Show summary of missing data before bulk send."""
    no_ranking = sum(1 for l in leads_info if not l.get("ranking_grade") or l["ranking_grade"] == "?")
    no_website = sum(1 for l in leads_info if not l.get("website"))

    if no_ranking > 0 or no_website > 0:
        parts = []
        if no_ranking > 0:
            parts.append(f"**{no_ranking}** ohne Ranking")
        if no_website > 0:
            parts.append(f"**{no_website}** ohne Website")
        st.warning(f"Achtung: {' / '.join(parts)} von {len(leads_info)} Leads")


def _render_single_send(leads, template_choices, smtp_cfg, draft, signature):
    def _fmt_lead(i):
        l = leads[i]
        grade = l.get("ranking_grade") or "?"
        return f"{l['firma']} | {l.get('stadt') or '-'} | {l['email']} | Ranking: {grade}"

    idx = st.selectbox(
        "Lead auswaehlen",
        range(len(leads)),
        format_func=_fmt_lead,
        key="single_lead_sel",
    )
    lead = leads[idx]

    _render_lead_data_check(lead)

    sent_to_lead = lead.get("email_count", 0)
    email_type = detect_email_type(sent_to_lead)
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

    kc1, kc2, kc3 = st.columns([2, 1, 1])
    with kc1:
        template_name = st.selectbox("Template", list(template_choices.keys()), key="single_tpl")
    with kc2:
        st.markdown(
            f'<div style="margin-top:28px;">'
            f'<span style="background:{type_color}35;color:{type_color};'
            f'border:1px solid {type_color}55;padding:4px 10px;border-radius:12px;'
            f'font-weight:600;font-size:0.8rem;">{type_label}</span>'
            f'<span style="color:#b8bec6;font-size:0.85rem;margin-left:6px;">'
            f'{sent_to_lead} gesendet</span></div>',
            unsafe_allow_html=True,
        )
    with kc3:
        ki_btn = st.button("🤖 KI Mail erstellen", key="single_ki_gen")

    if ki_btn:
        with st.spinner("KI generiert E-Mail..."):
            try:
                result = api_client.generate_email(lead["id"], email_type)
                if result.get("betreff"):
                    st.session_state["ki_single_draft"] = {
                        "betreff": result["betreff"],
                        "inhalt": result.get("inhalt", ""),
                    }
                elif result.get("raw"):
                    st.warning("KI-Antwort konnte nicht verarbeitet werden.")
                    st.text(result["raw"])
            except Exception as e:
                st.error(f"Fehler: {e}")

    ki_draft = st.session_state.get("ki_single_draft")
    tpl = template_choices[template_name]

    if ki_draft:
        betreff = ki_draft["betreff"]
        inhalt = ki_draft["inhalt"]
    elif draft and template_name == "Eigene E-Mail":
        betreff = draft.get("betreff", "")
        inhalt = draft.get("inhalt", "")
    elif tpl:
        betreff = tpl["betreff"]
        inhalt = tpl["inhalt"]
    else:
        betreff = ""
        inhalt = ""

    for key, value in variables.items():
        betreff = betreff.replace(f"{{{key}}}", str(value))
        inhalt = inhalt.replace(f"{{{key}}}", str(value))

    with st.form("send_email_form"):
        betreff_input = st.text_input("Betreff", value=betreff)
        inhalt_input = st.text_area("Inhalt", value=inhalt, height=300)

        append_sig = False
        if signature:
            append_sig = st.checkbox("✍️ Signatur anfügen", value=True)

        send = st.form_submit_button("📤 E-Mail senden", type="primary")

    final_body = inhalt_input
    if append_sig and signature:
        final_body = inhalt_input + "\n\n-- \n" + signature

    with st.expander("Vorschau anzeigen"):
        preview_body = final_body.replace("\n", "<br>")
        st.markdown(
            f'<div class="email-preview">'
            f'<div class="ep-to">An: {lead["email"]}</div>'
            f'<div class="ep-subject">{betreff_input}</div>'
            f'<hr style="border-color:#2a3040;opacity:0.4;">'
            f'<div class="ep-body">{preview_body}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if send:
        st.session_state["email_confirm"] = {
            "lead_id": lead["id"],
            "lead_firma": lead["firma"],
            "lead_email": lead["email"],
            "betreff": betreff_input,
            "inhalt": final_body,
        }

    from_email = smtp_cfg.get("from_email", "")
    action, test_addr = render_send_confirm("email_confirm", default_test_email=from_email)
    if action == "send":
        confirm = st.session_state["email_confirm"]
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
        del st.session_state["email_confirm"]
        st.session_state.pop("ki_single_draft", None)
        if draft:
            st.session_state.pop("outreach_draft", None)
    elif action == "test":
        st.info("Test-Mails über eigene Adresse: Bitte direkt senden und Betreff mit [TEST] markieren.")


def _render_bulk_send(leads, template_choices, smtp_cfg, signature):
    def _fmt_lead(i):
        l = leads[i]
        return f"{l['firma']} | {l.get('stadt') or '-'} | {l['email']}"

    selected_indices = st.multiselect(
        "Leads auswählen",
        range(len(leads)),
        format_func=_fmt_lead,
    )

    template_name = st.selectbox("Template", list(template_choices.keys()), key="bulk_tpl")
    tpl = template_choices[template_name]

    bc1, bc2 = st.columns(2)
    with bc1:
        append_sig = False
        if signature:
            append_sig = st.checkbox("✍️ Signatur anfügen", value=True, key="bulk_sig")
    with bc2:
        bulk_delay = st.slider(
            "Verzögerung zwischen Mails (Sek.)",
            min_value=5, max_value=120, value=30, step=5,
            key="bulk_delay",
        )

    if st.button(f"📤 An {len(selected_indices)} Leads senden", type="primary", disabled=len(selected_indices) == 0):
        leads_info = []
        for idx in selected_indices:
            l = leads[idx]
            leads_info.append({
                "id": l["id"], "firma": l["firma"], "email": l["email"],
                "stadt": l.get("stadt") or "", "kategorie": l.get("kategorie", "anwalt"),
                "website": l.get("website") or "",
                "ranking_grade": l.get("ranking_grade") or "?",
                "ranking_score": l.get("ranking_score") or "?",
            })
        st.session_state["bulk_confirm"] = {
            "leads": leads_info,
            "tpl": tpl,
            "template_name": template_name,
            "append_sig": append_sig,
            "bulk_delay": bulk_delay,
        }

    bulk_data = st.session_state.get("bulk_confirm")
    if bulk_data:
        _render_bulk_data_summary(bulk_data["leads"])
        with st.container(border=True):
            st.markdown(f"#### Bulk-Versand bestätigen: {len(bulk_data['leads'])} Leads")
            for li in bulk_data["leads"][:10]:
                st.markdown(f"- **{li['firma']}** — `{li['email']}`")
            if len(bulk_data["leads"]) > 10:
                st.caption(f"+ {len(bulk_data['leads']) - 10} weitere...")
            st.markdown(f"**Template:** {bulk_data['template_name']} · **Delay:** {bulk_data['bulk_delay']}s")

            bb1, bb2 = st.columns(2)
            with bb1:
                bulk_real = st.button("📤 Jetzt senden", type="primary", key="bulk_confirm_real")
            with bb2:
                bulk_cancel = st.button("❌ Abbrechen", key="bulk_confirm_cancel")

        if bulk_cancel:
            del st.session_state["bulk_confirm"]
            st.rerun()

        if bulk_real:
            _execute_bulk_send(st.session_state["bulk_confirm"], smtp_cfg, signature)
            del st.session_state["bulk_confirm"]


def _fill_template(tpl, lead_info, smtp_cfg, signature, append_sig):
    betreff = tpl["betreff"] if tpl else ""
    inhalt = tpl["inhalt"] if tpl else ""

    rec_product = get_recommended_product(lead_info.get("kategorie", "anwalt"))

    variables = {
        "firma": lead_info.get("firma", ""),
        "stadt": lead_info.get("stadt") or "Schweiz",
        "website": lead_info.get("website") or "",
        "ranking_grade": str(lead_info.get("ranking_grade") or "?"),
        "ranking_score": str(lead_info.get("ranking_score") or "?"),
        "absender_name": smtp_cfg.get("from_name", ""),
        "produkt": rec_product.get("name", "Rapid Header Fix"),
        "preis": rec_product.get("preis", "CHF 490.–"),
    }
    for key, value in variables.items():
        betreff = betreff.replace(f"{{{key}}}", str(value))
        inhalt = inhalt.replace(f"{{{key}}}", str(value))

    if append_sig and signature:
        inhalt = inhalt + "\n\n-- \n" + signature

    return betreff, inhalt


def _execute_bulk_send(bulk_data, smtp_cfg, signature):
    tpl = bulk_data["tpl"]
    append_sig = bulk_data["append_sig"]
    bulk_delay_val = bulk_data["bulk_delay"]

    lead_ids = [li["id"] for li in bulk_data["leads"]]
    subject_tpl = tpl["betreff"] if tpl else ""
    body_tpl = tpl["inhalt"] if tpl else ""

    if append_sig and signature:
        body_tpl = body_tpl.rstrip() + "\n\n-- \n" + signature

    try:
        resp = api_client.start_bulk_email(
            lead_ids=lead_ids,
            subject=subject_tpl,
            body=body_tpl,
            delay_seconds=bulk_delay_val,
        )
        job_id = resp.get("job_id")
        if not job_id:
            st.error("Bulk-Job konnte nicht gestartet werden.")
            return
    except Exception as e:
        st.error(f"Fehler beim Starten: {e}")
        return

    progress = st.progress(0)
    status_text = st.empty()

    while True:
        try:
            job = api_client.get_bulk_email_status(job_id)
        except Exception:
            time.sleep(2)
            continue

        completed = job.get("completed", 0)
        total = job.get("total", len(lead_ids))
        sent = job.get("sent", 0)
        errors = job.get("errors", 0)

        progress.progress(min(1.0, completed / max(1, total)))
        status_text.text(f"Gesendet: {sent} / Fehler: {errors} / Gesamt: {completed}/{total}")

        if job.get("status") in ("done", "error"):
            break

        time.sleep(3)

    progress.progress(1.0)
    status_text.text("Fertig!")
    st.success(f"Gesendet: {sent} | Fehlgeschlagen: {errors}")


def _render_templates_tab():
    st.subheader("E-Mail Templates")

    # Handle Outlook draft creation
    outlook_draft = st.session_state.get("outlook_draft")
    if outlook_draft:
        with st.container(border=True):
            st.markdown("#### 📧 Als Outlook-Entwurf erstellen")
            st.caption(f"Quelle: {outlook_draft.get('source', 'Unbekannt')}")

            preview_betreff = st.text_input("Betreff", value=outlook_draft.get("betreff", ""), key="outlook_betreff")
            preview_inhalt = st.text_area("Inhalt", value=outlook_draft.get("inhalt", ""), height=200, key="outlook_inhalt")

            od1, od2 = st.columns(2)
            with od1:
                if st.button("✅ In Outlook erstellen", type="primary", key="confirm_outlook_draft"):
                    try:
                        result = api_client.send_to_outlook_draft(
                            subject=preview_betreff,
                            body=preview_inhalt
                        )
                        if result.get("success"):
                            st.success(f"✅ Entwurf erstellt!")
                            web_link = result.get("web_link", "")
                            if web_link:
                                st.markdown(f"[Entwurf in Outlook öffnen]({web_link})")
                            del st.session_state["outlook_draft"]
                            st.rerun()
                        else:
                            st.error(f"Fehler: {result.get('error', 'Unbekannt')}")
                    except Exception as e:
                        st.error(f"Fehler: {str(e)}")
            with od2:
                if st.button("❌ Abbrechen", key="cancel_outlook_draft"):
                    del st.session_state["outlook_draft"]
                    st.rerun()

        st.divider()

    # Check Outlook configuration
    try:
        outlook_config = api_client.get_outlook_configured()
        outlook_configured = outlook_config.get("configured", False)
    except Exception:
        outlook_configured = False

    try:
        default_templates = cached_templates()
    except Exception:
        default_templates = []

    st.write("#### Standard Templates")
    for t in default_templates:
        with st.expander(t['name']):
            st.write(f"**Betreff:** {t['betreff']}")
            st.text_area("Inhalt", value=t["inhalt"], height=200, key=f"default_{t['key']}", disabled=True)

            # Add Outlook draft button for default templates too
            if outlook_configured:
                if st.button(f"📧 Als Outlook-Entwurf", key=f"outlook_default_{t['key']}"):
                    st.session_state["outlook_draft"] = {
                        "betreff": t["betreff"],
                        "inhalt": t["inhalt"],
                        "source": f"Standard: {t['name']}"
                    }

    st.write("#### Benutzerdefinierte Templates")
    try:
        custom = cached_custom_templates()
    except Exception:
        custom = []

    for template in custom:
        with st.expander(template['name']):
            st.write(f"**Betreff:** {template['betreff']}")
            st.text_area("Inhalt", value=template["inhalt"], height=150, key=f"view_{template['id']}", disabled=True)

            ec1, ec2, ec3 = st.columns(3)
            with ec1:
                if st.button("✏️ Bearbeiten", key=f"edit_{template['id']}"):
                    st.session_state[f"editing_{template['id']}"] = True
            with ec2:
                if st.button("🗑️ Löschen", key=f"del_{template['id']}"):
                    try:
                        api_client.delete_custom_template(template["id"])
                        invalidate_templates()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
            with ec3:
                if outlook_configured:
                    if st.button("📧 An Outlook", key=f"outlook_{template['id']}"):
                        st.session_state["outlook_draft"] = {
                            "betreff": template["betreff"],
                            "inhalt": template["inhalt"],
                            "source": f"Custom: {template['name']}"
                        }
                else:
                    st.caption("Outlook nicht konfiguriert")

            if st.session_state.get(f"editing_{template['id']}"):
                with st.form(f"edit_form_{template['id']}"):
                    new_name = st.text_input("Name", value=template["name"])
                    new_betreff = st.text_input("Betreff", value=template["betreff"])
                    new_inhalt = st.text_area("Inhalt", value=template["inhalt"], height=150)
                    if st.form_submit_button("💾 Aktualisieren"):
                        try:
                            api_client.update_custom_template(template["id"], new_name, new_betreff, new_inhalt)
                            invalidate_templates()
                            st.session_state[f"editing_{template['id']}"] = False
                            st.success("Template aktualisiert!")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

    st.write("#### Neues Template")
    with st.form("new_template"):
        name = st.text_input("Name")
        betreff = st.text_input("Betreff")
        inhalt = st.text_area("Inhalt", height=150)
        if st.form_submit_button("💾 Speichern"):
            try:
                api_client.create_custom_template(name, betreff, inhalt)
                invalidate_templates()
                st.success("Template gespeichert!")
                st.rerun()
            except Exception as e:
                st.error(str(e))


@st.fragment
def _render_history_tab():
    st.subheader("E-Mail Verlauf")

    try:
        history = api_client.get_global_email_history(limit=50)
    except Exception:
        history = []

    if history:
        for item in history:
            status_label = "Gesendet" if item.get("status") == "sent" else "Fehler" if item.get("status") == "failed" else "Entwurf"
            firma = item.get("lead_firma") or "?"
            d = item.get("gesendet_at", "-")
            if isinstance(d, str) and "T" in d:
                try:
                    dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
                    d = dt.strftime("%d.%m.%Y %H:%M")
                except Exception:
                    pass

            with st.expander(f"{status_label} -- {firma} -- {item.get('betreff', '')}"):
                st.write(f"**Status:** {item.get('status', '-')}")
                st.write(f"**Datum:** {d}")
                st.text_area("Inhalt", value=item.get("inhalt", ""), height=100, disabled=True, key=f"hist_{item['id']}")
    else:
        st.info("Noch keine E-Mails gesendet.")
