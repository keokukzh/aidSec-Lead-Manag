import pandas as pd

input_file = r"c:\Users\aidevelo\Desktop\Praxen leads\praxen_leads_bereinigt.xlsx"

df = pd.read_excel(input_file, sheet_name="Anwalts Kanzleien")
for col in df.columns:
    df[col] = df[col].astype(str).replace('nan', '')

print(f"=== ANWALTS KANZLEIEN - FINALE ÜBERSICHT ===\n")
print(f"Gesamteinträge: {len(df)}")
print(f"Spalten: {list(df.columns)}\n")

print(f"{'Nr':>3} | {'Firma':<38} | {'Website':<33} | {'E-Mail':<7} | {'Stadt':<18} | {'Tel':<7} | {'WP'}")
print("-" * 135)
for idx, row in df.iterrows():
    firma = str(row['Firma'])[:37] if row['Firma'] != '' else 'LEER'
    website = str(row['Website'])[:32] if row['Website'] != '' else 'LEER'
    email = 'OK' if row['EMail'] != '' else 'FEHLT'
    stadt = str(row['Stadt'])[:17] if row['Stadt'] != '' else 'FEHLT'
    tel = 'OK' if row['Telefon'] != '' else 'FEHLT'
    wp = str(row['WordPress'])
    print(f"{idx+1:3} | {firma:<38} | {website:<33} | {email:<7} | {stadt:<18} | {tel:<7} | {wp}")

print(f"\n=== STATISTIKEN ===")
filled_email = len(df[df['EMail'] != ''])
filled_phone = len(df[df['Telefon'] != ''])
filled_city = len(df[df['Stadt'] != ''])
filled_firma = len(df[df['Firma'] != ''])

print(f"Firmennamen:    {filled_firma}/{len(df)} ({filled_firma/len(df)*100:.0f}%)")
print(f"E-Mail:         {filled_email}/{len(df)} ({filled_email/len(df)*100:.0f}%)")
print(f"Telefon:        {filled_phone}/{len(df)} ({filled_phone/len(df)*100:.0f}%)")
print(f"Stadt:          {filled_city}/{len(df)} ({filled_city/len(df)*100:.0f}%)")
print(f"WordPress:      {len(df[df['WordPress'] == 'Ja'])}/{len(df)} (100%)")

print(f"\n=== EINTRÄGE MIT FEHLENDEN DATEN ===")
for idx, row in df.iterrows():
    missing = []
    if row['EMail'] == '': missing.append('E-Mail')
    if row['Telefon'] == '': missing.append('Telefon')
    if row['Stadt'] == '': missing.append('Stadt')
    if missing:
        print(f"  {idx+1}. {row['Firma'][:35]:<35} ({row['Website'][:30]}) -> fehlt: {', '.join(missing)}")
