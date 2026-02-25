import pandas as pd

input_file = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"
df = pd.read_excel(input_file)

print(f"Gesamteinträge: {len(df)}")

wp_yes = (df['WordPress'] == 'Ja').sum()
wp_no = (df['WordPress'] == 'Nein').sum()
wp_empty = df['WordPress'].isna().sum() + (df['WordPress'].astype(str).str.strip() == '').sum()

print(f"\nWordPress-Status:")
print(f"  Ja: {wp_yes}")
print(f"  Nein: {wp_no}")
print(f"  Leer: {wp_empty}")
