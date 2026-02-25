import sys
sys.path.insert(0, ".")
from services.ranking_service import get_ranking_service

svc = get_ranking_service()
r = svc.check_url("https://www.praxis-meierhof.ch/")
print("Grade:", r.get("grade"))
print("Score:", r.get("score"))
print("Error:", r.get("error", "None"))
print("Headers:")
for h in r.get("headers", []):
    print(f"  {h['name']}: {h['value']} ({h['rating']})")
