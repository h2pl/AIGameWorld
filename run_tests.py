import subprocess, sys

cwd = r"E:\Projects\SimGameWorld\backend"

tests = [
    ("Unit Tests", ["uv", "run", "pytest", "tests/unit", "-q", "--tb=short"]),
    ("Integration Tests", ["uv", "run", "pytest", "tests/integration", "-q", "--tb=short"]),
]

all_ok = True
for name, cmd in tests:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    print(f"\n=== {name} === (rc={r.returncode})")
    if r.stdout:
        print(r.stdout[-500:])
    if r.stderr and "passed" not in r.stderr.lower():
        print("STDERR:", r.stderr[-300:])
    if r.returncode != 0:
        all_ok = False

sys.exit(0 if all_ok else 1)
