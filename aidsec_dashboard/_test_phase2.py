"""Phase 2 API smoke tests — all endpoints."""
import requests
import sys

BASE = "http://127.0.0.1:8000/api"
passed = 0
failed = 0


def test(name, method, path, expected_status=200, **kwargs):
    global passed, failed
    try:
        r = getattr(requests, method)(f"{BASE}{path}", **kwargs)
        if r.status_code == expected_status:
            passed += 1
            print(f"  OK  {name} [{r.status_code}]")
            return r
        else:
            failed += 1
            detail = r.text[:200] if r.text else ""
            print(f"  FAIL {name} — expected {expected_status}, got {r.status_code}: {detail}")
            return r
    except Exception as e:
        failed += 1
        print(f"  ERR  {name} — {e}")
        return None


print("=== Phase 2 API Tests ===\n")

# Health
print("-- Health --")
test("health", "get", "/health")

# Leads (from Phase 1)
print("\n-- Leads --")
r = test("list leads", "get", "/leads?page=1&per_page=3")
if r and r.status_code == 200:
    data = r.json()
    lead_id = data["items"][0]["id"] if data["items"] else None
    print(f"     total={data['total']}, first_id={lead_id}")
else:
    lead_id = None

if lead_id:
    test("get lead", "get", f"/leads/{lead_id}")
    test("update lead", "patch", f"/leads/{lead_id}", json={"notes": "API test note"})

# Dashboard
print("\n-- Dashboard --")
test("dashboard kpis", "get", "/dashboard/kpis")

# Emails
print("\n-- Emails --")
if lead_id:
    test("email history", "get", f"/emails/history/{lead_id}")
test("email templates", "get", "/emails/templates")
test("smtp test", "post", "/emails/smtp-test")
test("daily count", "get", "/emails/daily-count")

# Ranking
print("\n-- Ranking --")
test("ranking check", "post", "/ranking/check", json={"url": "example.com"})
if lead_id:
    r = test("ranking check lead", "post", f"/ranking/check-lead/{lead_id}")

# Campaigns
print("\n-- Campaigns --")
r = test("list campaigns", "get", "/campaigns")
r = test("create campaign", "post", "/campaigns", expected_status=201,
         json={"name": "API Test Campaign", "sequenz": [
             {"typ": "erstkontakt", "delay_tage": 0},
             {"typ": "nachfassen", "delay_tage": 3},
         ]})
if r and r.status_code == 201:
    camp_id = r.json()["id"]
    test("get campaign", "get", f"/campaigns/{camp_id}")
    test("campaign leads", "get", f"/campaigns/{camp_id}/leads")
    if lead_id:
        test("assign leads", "post", f"/campaigns/{camp_id}/leads",
             json={"lead_ids": [lead_id]})
    test("update campaign", "patch", f"/campaigns/{camp_id}",
         json={"beschreibung": "Test description"})
    test("delete campaign", "delete", f"/campaigns/{camp_id}", expected_status=204)

# Follow-ups
print("\n-- Follow-ups --")
test("list followups", "get", "/followups")
test("list followups pending", "get", "/followups?due=pending")
if lead_id:
    r = test("create followup", "post", "/followups", expected_status=201,
             json={"lead_id": lead_id, "datum": "2026-03-01T10:00:00", "notiz": "API test"})
    if r and r.status_code == 201:
        fu_id = r.json()["id"]
        test("update followup", "patch", f"/followups/{fu_id}",
             json={"erledigt": True})
        test("delete followup", "delete", f"/followups/{fu_id}", expected_status=204)

# Settings
print("\n-- Settings --")
test("list settings", "get", "/settings")
test("get setting", "get", "/settings/page_size")
test("put setting", "put", "/settings/test_key", json={"value": "test_val"})
test("get smtp config", "get", "/config/smtp")
test("get llm config", "get", "/config/llm")
test("get products", "get", "/config/products")

# Import/Export
print("\n-- Export --")
test("export csv", "get", "/export/csv")
test("export excel", "get", "/export/excel")

# Marketing
print("\n-- Marketing --")
test("list ideas", "get", "/marketing/ideas")
test("get idea", "get", "/marketing/ideas/1")
test("list tracker", "get", "/marketing/tracker")
r = test("add to tracker", "post", "/marketing/tracker", expected_status=201,
         json={"idea_number": 999, "status": "geplant", "prioritaet": 1})
if r and r.status_code == 201:
    t_id = r.json()["id"]
    test("update tracker", "patch", f"/marketing/tracker/{t_id}",
         json={"status": "aktiv"})
    test("delete tracker", "delete", f"/marketing/tracker/{t_id}", expected_status=204)

# Agents (just status check, no LLM call)
print("\n-- Agents --")
test("llm status", "get", "/agents/llm-status")

print(f"\n=== Results: {passed} passed, {failed} failed ===")
sys.exit(1 if failed else 0)
