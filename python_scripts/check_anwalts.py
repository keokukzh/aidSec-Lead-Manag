import pandas as pd

input_file = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"

# Read Anwalts Kanzleien sheet
df = pd.read_excel(input_file, sheet_name="Anwalts Kanzleien")

print(f"Gesamteinträge: {len(df)}")
print(f"Spalten: {list(df.columns)}")

# Show all entries
print("\nAlle Einträge:")
for idx, row in df.iterrows():
    firma = str(row['Firma'])[:35] if not pd.isna(row['Firma']) else 'LEER'
    website = str(row['Website'])[:30] if not pd.isna(row['Website']) else 'LEER'
    email = 'OK' if not pd.isna(row['EMail']) and str(row['EMail']).strip() != '' else 'FEHLT'
    stadt = str(row['Stadt'])[:15] if not pd.isna(row['Stadt']) and str(row['Stadt']).strip() != '' else 'FEHLT'
    tel = 'OK' if not pd.isna(row['Telefon']) and str(row['Telefon']).strip() != '' else 'FEHLT'
    print(f"{idx+1:3}. {firma:<35} | {website:<30} | E:{email:<6} | S:{stadt:<15} | T:{tel}")

# Check duplicates
print(f"\n--- Duplikate (Website) ---")
def normalize_url(url):
    url = str(url).strip().lower().rstrip('/')
    url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    return url

df['url_norm'] = df['Website'].apply(normalize_url)
dupes = df[df.duplicated(subset=['url_norm'], keep=False)]
if len(dupes) > 0:
    print(f"Duplikate gefunden: {len(dupes)}")
    for idx, row in dupes.iterrows():
        print(f"  - {row['Firma']}: {row['Website']}")
else:
    print("Keine Duplikate gefunden")
