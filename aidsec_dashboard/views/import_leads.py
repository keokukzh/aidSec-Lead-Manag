"""Import Page - Import Leads from Excel/CSV — powered by API"""
import streamlit as st
import os
import pandas as pd
import api_client
from cache_helpers import cached_dashboard_kpis, invalidate_leads
from utils.importer import import_from_excel, import_csv, import_direct


def _read_excel_stats(file_path: str):
    stats = {}
    try:
        xls = pd.ExcelFile(file_path)
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            stats[sheet] = len(df)
    except Exception:
        pass
    return stats


def render():
    st.title("📥 Import Leads")

    default_path = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"
    file_exists = os.path.exists(default_path)

    try:
        check = api_client.get_leads(page=1, per_page=1)
        current_leads = check.get("total", 0)
    except Exception:
        current_leads = 0

    st.sidebar.markdown("### 📊 Aktuelle Datenbank")
    st.sidebar.metric("Vorhandene Leads", current_leads)

    if current_leads > 0:
        try:
            kpis = cached_dashboard_kpis()
            k = kpis["kategorie"]
            st.sidebar.write(f"- Anwälte: {k['anwalt']}")
            st.sidebar.write(f"- Praxen: {k['praxis']}")
            st.sidebar.write(f"- WordPress/Diverse: {k['wordpress']}")
        except Exception:
            pass

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📊 Excel Import", "📄 CSV Import", "➕ Einzelner Lead"])

    with tab1:
        st.subheader("Excel Import (Anwalts Kanzleien + Praxen Leads)")
        st.write("Importieren Sie Leads aus der bestehenden Excel-Datei.")

        excel_path = None

        if file_exists:
            st.success("✅ Excel-Datei gefunden: `praxen_leads_bereinigt.xlsx`")

            sheet_stats = _read_excel_stats(default_path)
            if sheet_stats:
                cols = st.columns(len(sheet_stats) + 1)
                total_rows = 0
                for i, (sheet, count) in enumerate(sheet_stats.items()):
                    cols[i].metric(sheet, count)
                    total_rows += count
                cols[-1].metric("Total", total_rows)

            st.info(f"**Pfad:** `{default_path}`")
            excel_path = default_path

            with st.expander("Vorschau (erste 10 Zeilen pro Sheet)"):
                try:
                    xls = pd.ExcelFile(default_path)
                    for sheet in xls.sheet_names:
                        st.write(f"**{sheet}:**")
                        df_preview = pd.read_excel(xls, sheet_name=sheet, nrows=10)
                        st.dataframe(df_preview, width="stretch", hide_index=True)
                except Exception as e:
                    st.error(f"Vorschau-Fehler: {e}")
        else:
            st.error(f"⚠️ Excel-Datei nicht gefunden unter: `{default_path}`")
            st.write("---")
            st.write("**Oder Datei hochladen:**")
            excel_file = st.file_uploader("Excel-Datei auswählen", type=["xlsx"], key="excel_uploader")

            if excel_file:
                temp_path = os.path.join(os.path.dirname(__file__), "..", "data", "temp_upload.xlsx")
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)

                with open(temp_path, "wb") as f:
                    f.write(excel_file.getbuffer())

                sheet_stats = _read_excel_stats(temp_path)
                if sheet_stats:
                    cols = st.columns(len(sheet_stats) + 1)
                    total_rows = 0
                    for i, (sheet, count) in enumerate(sheet_stats.items()):
                        cols[i].metric(sheet, count)
                        total_rows += count
                    cols[-1].metric("Total", total_rows)

                with st.expander("Vorschau"):
                    try:
                        xls = pd.ExcelFile(temp_path)
                        for sheet in xls.sheet_names:
                            st.write(f"**{sheet}:**")
                            df_preview = pd.read_excel(xls, sheet_name=sheet, nrows=10)
                            st.dataframe(df_preview, width="stretch", hide_index=True)
                    except Exception as e:
                        st.error(f"Vorschau-Fehler: {e}")

                excel_path = temp_path

        if excel_path:
            if st.button("🚀 Jetzt importieren", type="primary"):
                try:
                    import_excel_to_db(excel_path)
                finally:
                    if excel_path != default_path:
                        try:
                            os.remove(excel_path)
                        except Exception:
                            pass

    with tab2:
        st.subheader("CSV Import (WordPress/Diverse)")
        st.write("Importieren Sie WordPress/Diverse Leads aus einer CSV-Datei.")

        csv_file = st.file_uploader("CSV-Datei auswählen", type=["csv"])

        if csv_file:
            temp_path = os.path.join(os.path.dirname(__file__), "..", "data", "temp_csv.csv")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(csv_file.getbuffer())

            with st.expander("Vorschau"):
                try:
                    df_preview = pd.read_csv(temp_path, nrows=10)
                    st.dataframe(df_preview, width="stretch", hide_index=True)
                    st.write(f"**{len(pd.read_csv(temp_path))} Zeilen** in der Datei")
                except Exception as e:
                    st.error(f"Vorschau-Fehler: {e}")

            kategorie = st.selectbox("Kategorie", ["anwalt", "praxis", "wordpress"])

            if st.button("CSV importieren", type="primary"):
                try:
                    import_csv_to_db(temp_path, kategorie)
                finally:
                    try:
                        os.remove(temp_path)
                    except Exception:
                        pass
        else:
            st.info("Bitte eine CSV-Datei hochladen.")
            st.write("**CSV-Format:**")
            st.code("Firma,Website,EMail,Telefon,Stadt\nBeispiel AG,beispiel.ch,info@beispiel.ch,+41 79 123 45 67,Zürich")

    with tab3:
        st.subheader("Einzelner Lead")

        with st.form("single_lead_form"):
            col1, col2 = st.columns(2)

            with col1:
                firma = st.text_input("Firma *", placeholder="Firmenname")
                website = st.text_input("Website", placeholder="beispiel.ch")
                email = st.text_input("E-Mail", placeholder="info@beispiel.ch")

            with col2:
                telefon = st.text_input("Telefon", placeholder="+41 79 123 45 67")
                stadt = st.text_input("Stadt", placeholder="Zürich")
                kategorie = st.selectbox("Kategorie", ["anwalt", "praxis", "wordpress"])

            if st.form_submit_button("💾 Lead speichern", type="primary"):
                if firma:
                    try:
                        api_client.create_lead(
                            firma=firma,
                            website=website,
                            email=email,
                            telefon=telefon,
                            stadt=stadt,
                            kategorie=kategorie,
                            quelle="manual",
                        )
                        st.success(f"✅ Lead '{firma}' gespeichert!")
                    except api_client.APIError as e:
                        st.error(f"Fehler: {e.detail}")
                    except Exception as e:
                        st.error(f"Fehler: {e}")
                else:
                    st.error("Bitte geben Sie mindestens einen Firmennamen ein.")


def import_excel_to_db(file_path: str):
    """Import Excel file — still uses local importer + DB for bulk performance."""
    from database.database import get_session

    with st.spinner("Importiere Leads..."):
        leads_data, stats = import_from_excel(file_path)

        st.write("### 📊 Import Statistik")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gefunden", stats['total'])
        col2.metric("Praxen", stats['praxis'])
        col3.metric("Anwälte", stats['anwalt'])
        col4.metric("Fehler", stats['errors'])

        if stats['errors'] > 0:
            with st.expander(f"{stats['errors']} Validierungsfehler"):
                st.write("Einige Zeilen konnten nicht importiert werden (z.B. fehlende Firma).")

        if stats['total'] == 0:
            st.warning("Keine Leads in der Excel-Datei gefunden.")
            return

        session = get_session()
        try:
            imported, duplicates = import_direct(session, leads_data)
            st.success(f"✅ **{imported} Leads importiert!** ({duplicates} Duplikate übersprungen)")
        except Exception as e:
            st.error(f"Fehler beim Import: {e}")
            session.rollback()
        finally:
            session.close()


def import_csv_to_db(file_path: str, kategorie: str):
    """Import CSV file — still uses local importer + DB for bulk performance."""
    from database.database import get_session
    from database.models import LeadKategorie

    leads_data, stats = import_csv(file_path, LeadKategorie(kategorie))

    st.write("### 📊 Import Statistik")
    col1, col2, col3 = st.columns(3)
    col1.metric("Gefunden", stats['total'])
    col2.metric("Duplikate", stats['duplicates'])
    col3.metric("Fehler", stats['errors'])

    if stats['total'] == 0:
        st.warning("Keine Leads in der CSV-Datei gefunden.")
        return

    session = get_session()
    try:
        imported, duplicates = import_direct(session, leads_data)
        st.success(f"✅ **{imported} Leads importiert!**")
    except Exception as e:
        st.error(f"Fehler: {e}")
        session.rollback()
    finally:
        session.close()
