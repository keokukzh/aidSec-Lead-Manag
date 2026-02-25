import requests
import sys

url_base = "http://localhost:8000/api"
headers = {"X-API-Key": "05d55c1307cd521ec5d6b2c9fb1fef7092fbf91913dd5673fdce1b8dde60692f", "Content-Type": "application/json"}

print("Testing Feature 1: Security Scan...")
try:
    res = requests.post(f"{url_base}/leads/1/security-scan", headers=headers)
    print("Status Code:", res.status_code)
    print("Response:", res.text[:200])
except Exception as e:
    print("Exception on Feature 1:", e)

print("\nTesting Feature 2: Screenshot...")
try:
    res = requests.get(f"{url_base}/leads/1/screenshot", headers=headers)
    print("Status Code:", res.status_code)
    if res.status_code == 200:
        data = res.json()
        print("Success:", data.get("success"), "Grade:", data.get("grade"))
        b64 = data.get("screenshot_b64", "")
        print("Screenshot exists:", bool(b64), "Length:", len(b64) if b64 else 0)
    else:
        print("Response:", res.text)
except Exception as e:
    print("Exception on Feature 2:", e)

print("\nTesting Feature 3: Bulk Preview...")
try:
    payload = {
        "lead_ids": [1],
        "template": "praxis"
    }
    res = requests.post(f"{url_base}/emails/bulk-preview", headers=headers, json=payload)
    print("Status Code:", res.status_code)
    print("Response:", res.text[:500])
except Exception as e:
    print("Exception on Feature 3:", e)
