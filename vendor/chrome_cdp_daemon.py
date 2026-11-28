import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

_base_dir = Path(__file__).resolve().parent.parent
_default_prof = _base_dir / ".chrome-flow-accounts" / "acc_1"
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof = sys.argv[1] if len(sys.argv) > 1 else (
    str(_default_prof) if _default_prof.exists() else r"C:\videomaker\.chrome-gemini-profile"
)
port = sys.argv[2] if len(sys.argv) > 2 else "18800"
owner_pid = int(sys.argv[3]) if len(sys.argv) > 3 else os.getppid()
Path(prof).mkdir(parents=True, exist_ok=True)
runtime_dir = _base_dir / ".chrome-flow-accounts" / "runtime"
runtime_file = runtime_dir / f"port_{int(port)}.json"

# Se ja existe CDP vivo na porta, apenas aguardar enquanto responder.
# Nao criamos registro de ownership: esse Chrome pode ser de outro usuario/processo.
try:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
        print(f"CDP {port} already live: {r.read().decode()[:120]}", flush=True)
        while True:
            time.sleep(10)
except Exception:
    pass

cmd = [
    chrome,
    f"--remote-debugging-port={port}",
    f"--user-data-dir={prof}",
    "--no-first-run",
    "--no-default-browser-check",
    "--new-window",
    "https://flow.google.com/",
]
print("Starting Chrome CDP daemon:", " ".join(cmd), flush=True)
si = subprocess.STARTUPINFO()
si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
si.wShowWindow = 1  # SW_SHOWNORMAL: forca janela visivel mesmo quando herdada de processo oculto
p = subprocess.Popen(cmd, startupinfo=si)
record = {
    "port": int(port),
    "profile_dir": str(Path(prof).resolve()),
    "browser_pid": p.pid,
    "owner_pid": owner_pid,
    "account_id": Path(prof).name,
    "started_at": time.time(),
    "account": {
        "id": Path(prof).name,
        "cdp_port": int(port),
        "profile_dir": str(Path(prof).resolve()),
    },
}
try:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    tmp = runtime_file.with_suffix(f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(runtime_file))
except Exception as exc:
    print(f"AVISO: nao registrou ownership do Chrome {port}: {exc}", flush=True)

for _ in range(15):
    time.sleep(1)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=2) as r:
            print(f"CDP {port} READY:", r.read().decode()[:180], flush=True)
            break
    except Exception:
        pass
rc = p.wait()
print("Chrome exited with code:", rc, flush=True)
try:
    current = json.loads(runtime_file.read_text(encoding="utf-8"))
    if int(current.get("browser_pid") or 0) == p.pid:
        runtime_file.unlink(missing_ok=True)
except Exception:
    pass
