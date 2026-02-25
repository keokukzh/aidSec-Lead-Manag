import sqlite3
db = sqlite3.connect("data/leads.db")
try:
    db.execute("ALTER TABLE leads ADD COLUMN deal_size INTEGER DEFAULT 0;")
except Exception as e:
    print("deal_size error:", e)

try:
    db.execute("ALTER TABLE leads ADD COLUMN response_time_hours INTEGER DEFAULT 0;")
except Exception as e:
    print("response_time_hours error:", e)

db.commit()
db.close()
print("Schema updated successfully")
