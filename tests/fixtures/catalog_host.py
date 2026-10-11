"""SIMULATED host for adapter/protocol tests. This does not access Codex Cloud."""
import json
import os
import sys
import time
from datetime import datetime, timezone

mode = sys.argv[1] if len(sys.argv) > 1 else "catalog_ok"
if mode == "no_read":
    time.sleep(10)
    raise SystemExit(0)
request = json.loads(sys.stdin.readline())
if mode == "delay":
    time.sleep(10)
if mode == "invalid":
    print("not-json")
    raise SystemExit(0)
if mode == "oversized":
    sys.stdout.write("x" * (9 * 1024 * 1024))
    raise SystemExit(0)
if mode == "failed":
    print("SENSITIVE_RAW_OUTPUT_MUST_NOT_ESCAPE")
    raise SystemExit(5)
if mode == "check_environment":
    print(json.dumps({"secret_inherited": "TEST_AUTH_TOKEN" in os.environ}))
    raise SystemExit(0)
cloud = request["cloud_type"]
result = {"schema_version": 1, "cloud_type": cloud,
          "observed_at": datetime.now(timezone.utc).isoformat(),
          "account": "fixture-account", "account_verified": True,
          "content_type": "application/json"}
items = [{"id": "fixture-" + cloud, "name": "Simulated catalog record",
          "repository": {"id": 123, "full_name": "fixtures/demo"}, "published": True}]
if request["operation"] == "onboarding_read":
    items = [dict(item, configuration_id=item["id"]) for item in items]
if request["operation"] == "http_get":
    assert request["method"] == "GET"
    result.update(status=200, body={"items": items})
    if mode == "http_pages":
        if not request["query"].get("cursor"):
            result["body"]["next_cursor"] = "second"
        else:
            result["body"]["items"] = [dict(items[0], id="fixture-second")]
    if mode == "deny":
        result.update(status=403, body={"token": "DO_NOT_RETURN"})
        result.pop("observed_at")
    if mode == "html":
        result.update(content_type="text/html", body="Verification required")
else:
    result.update(status="ok", catalog={"items": items},
                  scope="user,workspace" if cloud == "current" else "user",
                  scopes=request.get("scopes", ["user", "workspace"] if cloud == "current" else ["user"]),
                  catalog_complete=True, include_drafts=request["include_drafts"])
    if mode == "unavailable":
        result.update(status="unavailable", catalog_complete=False, catalog={"items": []})
    if mode == "deny":
        result.update(status="forbidden")
        result.pop("observed_at")
    if mode == "empty":
        result.update(status="empty", catalog={"items": []})
if mode == "mismatch":
    result["cloud_type"] = "foreign"
if mode == "stale":
    result["observed_at"] = "2000-01-01T00:00:00+00:00"
print(json.dumps(result))
