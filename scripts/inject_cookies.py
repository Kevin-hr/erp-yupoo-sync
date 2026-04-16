import json
import subprocess

COOKIE_FILE = "C:/Users/Administrator/Documents/GitHub/ERP/logs/yupoo_cookies.json"

with open(COOKIE_FILE) as f:
    cookies = json.load(f)

print(f"Loaded {len(cookies)} cookies")

# Set each cookie
for i, ck in enumerate(cookies):
    domain = ck.get("domain", "").strip()
    name = ck.get("name", "")
    value = ck.get("value", "")

    if not name or not value or value == "deleted":
        continue

    # Build playwright-cli cookie-set command
    pw_cli = r"C:\Users\Administrator\AppData\Roaming\npm\playwright-cli"
    cmd = [
        pw_cli,
        "cookie-set",
        name,
        value,
        "--domain",
        domain,
        "--path",
        ck.get("path", "/"),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [{i}] FAILED: {name} = {value[:20]}...")
    else:
        print(f"  [{i}] OK: {name}")

print("\nDone setting cookies!")
