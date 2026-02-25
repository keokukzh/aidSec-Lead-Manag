import pandas as pd

input_file = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"
df = pd.read_excel(input_file)

print(f"Gesamteinträge: {len(df)}")

# Count missing
email_missing = df['EMail'].isna().sum() + (df['EMail'].astype(str).str.strip() == '').sum()
phone_missing = df['Telefon'].isna().sum() + (df['Telefon'].astype(str).str.strip() == '').sum()

print(f"Fehlende E-Mails: {email_missing}")
print(f"Fehlende Telefonnummern: {phone_missing}")

# Show entries with missing data
print("\n--- Einträge mit fehlenden Daten ---")
missing_data = df[(df['EMail'].isna() | (df['EMail'].astype(str).str.strip() == '')) | 
                  (df['Telefon'].isna() | (df['Telefon'].astype(str).str.strip() == ''))]

# Show first 20
print("\nEinträge mit fehlenden Daten (erste 20):")
for idx, row in missing_data.head(20).iterrows():
    email_status = "FEHLT" if pd.isna(row['EMail']) or str(row['EMail']).strip() == '' else "OK"
    phone_status = "FEHLT" if pd.isna(row['Telefon']) or str(row['Telefon']).strip() == '' else "OK"
    print(f"{idx+2}. {row['Firma'][:40]:<40} | {row['Website'][:30]:<30} | Email: {email_status:<6} | Tel: {phone_status}")
