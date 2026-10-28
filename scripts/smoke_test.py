"""Live HTTP process smoke test verifying health, security headers, and authentication gates."""
import sys
import httpx

def run_smoke_test(base_url: str = "http://127.0.0.1:8000"):
    print(f"[*] Executing live process smoke test against: {base_url}")
    client = httpx.Client(base_url=base_url, timeout=10.0, follow_redirects=False)

    passed = 0
    total = 4

    # 1. Health Live
    try:
        r = client.get("/health/live")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.json().get("status") == "alive"
        print("  [PASS] /health/live returned 200 OK with status: alive")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] /health/live error: {e}")

    # 2. Health Ready
    try:
        r = client.get("/health/ready")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.json().get("status") == "ready"
        print("  [PASS] /health/ready returned 200 OK with status: ready")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] /health/ready error: {e}")

    # 3. Security Headers on /login
    try:
        r = client.get("/login")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"
        print("  [PASS] /login returned 200 OK with strict security headers (nosniff, DENY)")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Security headers check error: {e}")

    # 4. Protected Route Denies Unauthenticated Request
    try:
        r = client.get("/datasets")
        assert r.status_code in (401, 302, 303), f"Expected 401 or redirect, got {r.status_code}"
        print("  [PASS] /datasets properly denies unauthenticated access")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Auth protection check error: {e}")

    print("--------------------------------------------------")
    print(f"Smoke Test Summary: {passed}/{total} checks passed.")
    if passed == total:
        print("[SUCCESS] All live server smoke tests passed.")
        return 0
    else:
        print("[ERROR] Some smoke tests failed.")
        return 1

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    sys.exit(run_smoke_test(url))
