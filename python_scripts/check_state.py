import pandas as pd

input_file = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"
df = pd.read_excel(input_file)

print(f"Gesamteinträge: {len(df)}")
print(f"Spalten: {list(df.columns)}")

# Count WordPress
if 'WordPress' in df.columns:
    wp_yes = (df['WordPress'] == 'Ja').sum()
    wp_no = (df['WordPress'] == 'Nein').sum()
    print(f"\nWordPress: Ja={wp_yes}, Nein={wp_no}")

# Missing data
email_missing = df['EMail'].isna().sum() + (df['EMail'].astype(str).str.strip() == '').sum()
phone_missing = df['Telefon'].isna().sum() + (df['Telefon'].astype(str).str.strip() == '').sum()
print(f"Fehlende E-Mails: {email_missing}")
print(f"Fehlende Telefone: {phone_missing}")
