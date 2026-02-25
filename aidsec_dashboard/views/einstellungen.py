"""Settings Page - Configuration — powered by API"""
import streamlit as st
import os
from dotenv import load_dotenv
from services.email_service import reset_email_service
from services.llm_service import reset_llm_service
import api_client
from cache_helpers import invalidate_settings, invalidate_email


def _get_setting_api(key: str, default: str = "") -> str:
    try:
        result = api_client.get_setting(key)
        return result.get("value", default) or default
    except Exception:
        return default


def _set_setting_api(key: str, value: str):
    try:
        api_client.put_setting(key, value)
    except Exception:
        pass


def render():
    """Render settings page"""
    st.title("⚙️ Einstellungen")

    tab1, tab2, tab3, tab4 = st.tabs(["📧 SMTP Einstellungen", "🤖 LLM Einstellungen", "🌐 Outlook / Microsoft 365", "🎛️ Allgemein"])

    # ==================== SMTP ====================
    with tab1:
        st.subheader("SMTP Konfiguration")

        load_dotenv()

        with st.form("smtp_form"):
            col1, col2 = st.columns(2)

            with col1:
                smtp_host = st.text_input(
                    "SMTP Host",
                    value=os.getenv("SMTP_HOST", ""),
                    placeholder="smtp.gmail.com"
                )
                smtp_port = st.number_input(
                    "SMTP Port",
                    value=int(os.getenv("SMTP_PORT") or 587),
                    min_value=1,
                    max_value=65535
                )

            with col2:
                smtp_username = st.text_input(
                    "Benutzername",
                    value=os.getenv("SMTP_USERNAME", ""),
                    placeholder="your@email.com"
                )
                smtp_password = st.text_input(
                    "Passwort",
                    type="password",
                    value=os.getenv("SMTP_PASSWORD", ""),
                    placeholder="App-Passwort"
                )

            smtp_from_name = st.text_input("Absendername", value=os.getenv("SMTP_FROM_NAME", "AidSec Team"))
            smtp_from_email = st.text_input("Absender-E-Mail", value=os.getenv("SMTP_FROM_EMAIL", "noreply@aidsec.ch"))

            if st.form_submit_button("💾 Speichern", type="primary"):
                save_smtp_settings(smtp_host, smtp_port, smtp_username, smtp_password, smtp_from_name, smtp_from_email)

        st.write("---")
        st.write("#### Verbindung testen")

        if st.button("🔗 Testen"):
            from services.email_service import get_email_service
            result = get_email_service().test_connection()
            if result.get("success"):
                st.success(result.get("message"))
            else:
                st.error(result.get("error"))

        st.write("---")
        st.write("#### E-Mail Signatur")
        st.caption("Signatur und Logo werden beim Versand automatisch als HTML-Mail eingebettet.")

        current_sig = _get_setting_api("email_signature", "")
        current_logo_b64 = _get_setting_api("signature_logo", "")
        current_logo_mime = _get_setting_api("signature_logo_mime", "")

        with st.form("signature_form"):
            signature = st.text_area(
                "Signatur-Text",
                value=current_sig,
                height=150,
                placeholder="Mit freundlichen Gruessen\n\nAid Destani\nAidSec IT-Sicherheit\naid.destani@aidsec.ch\n+41 76 462 29 99\naidsec.ch",
            )

            if st.form_submit_button("💾 Signatur speichern", type="primary"):
                _set_setting_api("email_signature", signature)
                invalidate_settings()
                st.success("Signatur-Text gespeichert!")

        st.write("**Logo**")
        if current_logo_b64:
            st.image(f"data:{current_logo_mime};base64,{current_logo_b64}", width=120)
            if st.button("🗑️ Logo entfernen"):
                _set_setting_api("signature_logo", "")
                _set_setting_api("signature_logo_mime", "")
                st.rerun()

        uploaded_logo = st.file_uploader(
            "Logo hochladen (PNG/JPG, max 200 KB empfohlen)",
            type=["png", "jpg", "jpeg"],
            key="sig_logo_upload",
        )
        if uploaded_logo is not None:
            import base64
            logo_bytes = uploaded_logo.read()
            logo_b64 = base64.b64encode(logo_bytes).decode("utf-8")
            mime = uploaded_logo.type or "image/png"
            _set_setting_api("signature_logo", logo_b64)
            _set_setting_api("signature_logo_mime", mime)
            st.success("Logo gespeichert!")
            st.rerun()

        if current_sig:
            with st.expander("Vorschau"):
                logo_html = ""
                if current_logo_b64:
                    logo_html = (
                        f'<img src="data:{current_logo_mime};base64,{current_logo_b64}" '
                        f'style="max-width:120px; margin-bottom:8px;" /><br>'
                    )
                st.markdown(
                    f'<div style="border-left:2px solid #00d4aa; padding-left:12px; '
                    f'color:#b8bec6; font-size:0.85rem;">'
                    f'{logo_html}'
                    f'<span style="white-space:pre-wrap;">{current_sig}</span></div>',
                    unsafe_allow_html=True,
                )

    # ==================== LLM ====================
    with tab2:
        st.subheader("LLM Konfiguration")

        provider_options = ["lm_studio", "openai_compatible"]
        provider_labels = {
            "lm_studio": "LM Studio (lokal)",
            "openai_compatible": "OpenAI-kompatibel (OpenAI, MiniMax, OpenRouter, Groq, ...)"
        }
        saved_provider = os.getenv("DEFAULT_PROVIDER", "lm_studio")
        if saved_provider == "openai":
            saved_provider = "openai_compatible"
        provider_index = provider_options.index(saved_provider) if saved_provider in provider_options else 0

        provider = st.selectbox(
            "LLM Provider",
            provider_options,
            index=provider_index,
            format_func=lambda x: provider_labels.get(x, x),
            key="llm_provider_select"
        )

        with st.form("llm_form"):
            if provider == "lm_studio":
                lm_url = st.text_input(
                    "LM Studio URL",
                    value=os.getenv("LM_STUDIO_URL", "http://localhost:1234/v1")
                )
                st.caption("LM Studio muss gestartet sein und Server aktiviert haben.")
                default_model = st.text_input(
                    "Default Model",
                    value=os.getenv("DEFAULT_MODEL", "llama-3"),
                    placeholder="llama-3, mistral, phi-3, ..."
                )
                openai_base_url = ""
                openai_key = ""
                openai_model = ""
            else:
                st.markdown(
                    '<span style="font-size:0.85rem;color:#b8bec6;">'
                    'Funktioniert mit jedem OpenAI-kompatiblen Anbieter. '
                    'Base URL anpassen je nach Provider.</span>',
                    unsafe_allow_html=True
                )
                openai_base_url = st.text_input(
                    "API Base URL",
                    value=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    placeholder="https://api.openai.com/v1",
                    help="OpenAI: https://api.openai.com/v1 | MiniMax: https://api.minimax.chat/v1 | "
                         "OpenRouter: https://openrouter.ai/api/v1 | Groq: https://api.groq.com/openai/v1 | "
                         "DeepSeek: https://api.deepseek.com/v1 | Together: https://api.together.xyz/v1"
                )
                openai_key = st.text_input(
                    "API Key",
                    type="password",
                    value=os.getenv("OPENAI_API_KEY", ""),
                    placeholder="sk-... / key-... / ..."
                )
                openai_model = st.text_input(
                    "Model",
                    value=os.getenv("OPENAI_MODEL", "gpt-4o"),
                    placeholder="gpt-4o, abab6.5-chat, mistral-large, llama-3-70b, ..."
                )
                lm_url = ""
                default_model = ""

            if st.form_submit_button("💾 Speichern", type="primary"):
                save_llm_settings(provider, lm_url, openai_base_url, openai_key, openai_model, default_model)

        st.write("---")
        st.write("#### Verfügbarkeit prüfen")

        if st.button("🔗 LLM testen"):
            from services.llm_service import get_llm_service
            llm = get_llm_service()
            with st.spinner("Teste Verbindung..."):
                result = llm.test_connection()
            if result.get("success"):
                st.success(f"✅ {result.get('detail', 'LLM ist verfügbar!')}")
            else:
                st.error(f"❌ {result.get('detail', 'LLM nicht verfügbar')}")

    # ==================== OUTLOOK ====================
    with tab3:
        st.subheader("Outlook / Microsoft 365")
        st.caption("E-Mail-Entwürfe direkt in Outlook erstellen.")

        st.info("""
        **Einrichtung:**
        1. Gehen Sie zu [Azure Portal](https://portal.azure.com)
        2. Registrieren Sie eine neue App
        3. Fügen Sie "Mail.Send" API-Berechtigung hinzu
        4. Erstellen Sie einen Client-Schlüssel
        5. Kopieren Sie Tenant ID, Client ID und Client Secret
        """)

        with st.form("outlook_form"):
            col1, col2 = st.columns(2)

            with col1:
                outlook_tenant_id = st.text_input(
                    "Tenant ID",
                    value=os.getenv("OUTLOOK_TENANT_ID", ""),
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                )
                outlook_client_id = st.text_input(
                    "Client ID",
                    value=os.getenv("OUTLOOK_CLIENT_ID", ""),
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                )

            with col2:
                outlook_client_secret = st.text_input(
                    "Client Secret",
                    type="password",
                    value=os.getenv("OUTLOOK_CLIENT_SECRET", ""),
                    placeholder="Ihr Client Secret"
                )
                outlook_user_email = st.text_input(
                    "Outlook E-Mail-Adresse",
                    value=os.getenv("OUTLOOK_USER_EMAIL", ""),
                    placeholder="ihre@email.onmicrosoft.com"
                )

            if st.form_submit_button("💾 Speichern", type="primary"):
                save_outlook_settings(outlook_tenant_id, outlook_client_id, outlook_client_secret, outlook_user_email)

        st.write("---")
        st.write("#### Verbindung testen")

        if st.button("🔗 Outlook-Verbindung testen"):
            from services.outlook_service import get_outlook_service
            outlook = get_outlook_service()
            with st.spinner("Teste Verbindung..."):
                result = outlook.test_connection()
            if result.get("success"):
                st.success(f"✅ {result.get('detail', 'Verbindung erfolgreich!')}")
            else:
                st.error(f"❌ {result.get('detail', 'Verbindung fehlgeschlagen')}")

    # ==================== ALLGEMEIN ====================
    with tab4:
        st.subheader("Allgemeine Einstellungen")
        st.write("App-Präferenzen (gespeichert in der Datenbank).")

        with st.form("general_settings"):
            page_size = st.selectbox(
                "Standard Leads pro Seite",
                ["25", "50", "100"],
                index=["25", "50", "100"].index(_get_setting_api("page_size", "50")),
            )

            default_view = st.selectbox(
                "Standard-Ansicht Leads",
                ["Liste", "Pipeline"],
                index=["Liste", "Pipeline"].index(_get_setting_api("default_view", "Liste")),
            )

            dashboard_recent = st.selectbox(
                "Dashboard: Neueste Leads Anzahl",
                ["10", "20", "50"],
                index=["10", "20", "50"].index(_get_setting_api("dashboard_recent", "20")),
            )

            ranking_delay = st.text_input(
                "Ranking: Standard-Verzögerung (Sek.)",
                value=_get_setting_api("ranking_delay", "0.5"),
            )

            if st.form_submit_button("💾 Speichern", type="primary"):
                _set_setting_api("page_size", page_size)
                _set_setting_api("default_view", default_view)
                _set_setting_api("dashboard_recent", dashboard_recent)
                _set_setting_api("ranking_delay", ranking_delay)
                invalidate_settings()
                st.success("✅ Einstellungen gespeichert!")

        st.markdown("---")
        st.write("#### Produkte / Services")
        st.caption("Diese Produkte erscheinen im Outreach Helper Agent.")

        import json as _json
        raw = _get_setting_api("products", "")
        try:
            products = _json.loads(raw) if raw else []
        except _json.JSONDecodeError:
            products = []

        if not products:
            products = [
                "Rapid Header Fix (CHF 490)",
                "Kanzlei-Härtung (CHF 950)",
                "Cyber-Mandat (CHF 89/Mt)",
            ]

        edited = st.data_editor(
            products,
            num_rows="dynamic",
            key="products_editor",
            column_config={"value": st.column_config.TextColumn("Produkt")},
        )

        if st.button("💾 Produkte speichern", key="save_products"):
            cleaned = [p for p in edited if p and str(p).strip()]
            _set_setting_api("products", _json.dumps(cleaned, ensure_ascii=False))
            st.success("Produkte gespeichert!")


def save_smtp_settings(host, port, username, password, from_name, from_email):
    """Save SMTP settings to .env"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    new_lines = []
    updated = {"SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_NAME", "SMTP_FROM_EMAIL"}

    for line in lines:
        key = line.split("=")[0] if "=" in line else ""
        if key in updated:
            if key == "SMTP_HOST":
                new_lines.append(f"SMTP_HOST={host}\n")
            elif key == "SMTP_PORT":
                new_lines.append(f"SMTP_PORT={port}\n")
            elif key == "SMTP_USERNAME":
                new_lines.append(f"SMTP_USERNAME={username}\n")
            elif key == "SMTP_PASSWORD":
                new_lines.append(f"SMTP_PASSWORD={password}\n")
            elif key == "SMTP_FROM_NAME":
                new_lines.append(f"SMTP_FROM_NAME={from_name}\n")
            elif key == "SMTP_FROM_EMAIL":
                new_lines.append(f"SMTP_FROM_EMAIL={from_email}\n")
        else:
            new_lines.append(line)

    keys_present = {l.split("=")[0] for l in new_lines if "=" in l}
    missing = {
        "SMTP_HOST": host,
        "SMTP_PORT": port,
        "SMTP_USERNAME": username,
        "SMTP_PASSWORD": password,
        "SMTP_FROM_NAME": from_name,
        "SMTP_FROM_EMAIL": from_email,
    }
    for key, val in missing.items():
        if key not in keys_present:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    load_dotenv(env_path, override=True)
    reset_email_service()
    invalidate_email()
    invalidate_settings()
    st.success("✅ SMTP-Einstellungen gespeichert!")


def save_llm_settings(provider, lm_url, openai_base_url, openai_key, openai_model, default_model):
    """Save LLM settings to .env"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    values = {
        "DEFAULT_PROVIDER": provider,
        "LM_STUDIO_URL": lm_url,
        "OPENAI_BASE_URL": openai_base_url,
        "OPENAI_API_KEY": openai_key,
        "OPENAI_MODEL": openai_model,
        "DEFAULT_MODEL": default_model,
    }

    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in values:
            new_lines.append(f"{key}={values[key]}\n")
        else:
            new_lines.append(line)

    keys_present = {l.split("=", 1)[0] for l in new_lines if "=" in l}
    for key, val in values.items():
        if key not in keys_present:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    load_dotenv(env_path, override=True)
    reset_llm_service()
    invalidate_settings()
    st.success("✅ LLM-Einstellungen gespeichert!")


def save_outlook_settings(tenant_id, client_id, client_secret, user_email):
    """Save Outlook settings to .env"""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")

    lines = []
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

    values = {
        "OUTLOOK_TENANT_ID": tenant_id,
        "OUTLOOK_CLIENT_ID": client_id,
        "OUTLOOK_CLIENT_SECRET": client_secret,
        "OUTLOOK_USER_EMAIL": user_email,
    }

    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in values:
            new_lines.append(f"{key}={values[key]}\n")
        else:
            new_lines.append(line)

    keys_present = {l.split("=", 1)[0] for l in new_lines if "=" in l}
    for key, val in values.items():
        if key not in keys_present:
            new_lines.append(f"{key}={val}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)

    load_dotenv(env_path, override=True)
    invalidate_settings()
    st.success("✅ Outlook-Einstellungen gespeichert!")
