import pandas as pd

input_file = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"
df = pd.read_excel(input_file)

print(f"Gesamteinträge: {len(df)}")
print(f"Spalten: {list(df.columns)}")

# Check WordPress status
wp_yes = (df['WordPress'] == 'Ja').sum()
wp_no = (df['WordPress'] == 'Nein').sum()
wp_empty = df['WordPress'].isna().sum() + (df['WordPress'].astype(str).str.strip() == '').sum()

print(f"\nWordPress-Status:")
print(f"  Ja: {wp_yes}")
print(f"  Nein: {wp_no}")
print(f"  Leer/Unbekannt: {wp_empty}")

# Show entries without WordPress status
print(f"\nEinträge ohne WordPress-Status (erste 30):")
empty_wp = df[(df['WordPress'].isna() | (df['WordPress'].astype(str).str.strip() == ''))]
for idx, row in empty_wp.head(30).iterrows():
    print(f"{idx+2}. {row['Firma'][:40]:<40} - {row['Website'][:30]}")
