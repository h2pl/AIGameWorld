import subprocess
cwd = r"E:\Projects\SimGameWorld\backend"
for name, cmd in [
    ("unit", ["uv", "run", "pytest", "tests/unit", "-q", "--tb=long"]),
    ("integration", ["uv", "run", "pytest", "tests/integration", "-q", "--tb=long"]),
]:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    path = rf"E:\Projects\SimGameWorld\test_{name}.log"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"rc={r.returncode}\n")
        f.write(r.stdout)
        if r.stderr:
            f.write("\n--- STDERR ---\n")
            f.write(r.stderr)
    print(f"[{name}] rc={r.returncode}")
    print(r.stdout[-200:] if r.stdout else "(no stdout)")
