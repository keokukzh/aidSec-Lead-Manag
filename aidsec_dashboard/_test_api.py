"""Quick API smoke test."""
import requests

BASE = "http://127.0.0.1:8000/api"

# Health
r = requests.get(f"{BASE}/health")
print(f"Health: {r.status_code} {r.json()}")

# Leads list
r = requests.get(f"{BASE}/leads", params={"page": 1, "per_page": 3})
data = r.json()
print(f"\nLeads: {r.status_code}, total={data['total']}, pages={data['pages']}")
for l in data["items"]:
    print(f"  - {l['firma']} | {l['status']} | {l['kategorie']} | grade={l.get('ranking_grade', '-')}")

# Dashboard KPIs
r = requests.get(f"{BASE}/dashboard/kpis")
kpis = r.json()
print(f"\nDashboard KPIs: {r.status_code}")
print(f"  Status: {kpis['status']}")
print(f"  Kategorie: {kpis['kategorie']}")
print(f"  Weekly: {kpis['weekly']}")
print(f"  Conversion: {kpis['conversion']}")
print(f"  Grades: {kpis['grades']}")
print(f"  Email: {kpis['email_stats']}")
print(f"  Follow-ups: {kpis['followups']}")

# Single lead detail
if data["items"]:
    lid = data["items"][0]["id"]
    r = requests.get(f"{BASE}/leads/{lid}")
    detail = r.json()
    print(f"\nLead detail (id={lid}): {r.status_code}")
    print(f"  {detail['firma']} | emails={detail['email_count']} | followups={detail['followup_count']}")

print("\n--- All tests passed! ---")
