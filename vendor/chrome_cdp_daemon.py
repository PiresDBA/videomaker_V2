import subprocess, sys, time, urllib.request
from pathlib import Path

chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
prof = sys.argv[1] if len(sys.argv) > 1 else r"C:\videomaker\.chrome-gemini-profile"
port = sys.argv[2] if len(sys.argv) > 2 else "18800"
Path(prof).mkdir(parents=True, exist_ok=True)

# Se ja existe CDP vivo na porta, apenas aguardar enquanto responder
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
si.wShowWindow = 1  # SW_SHOWNORMAL: forca janela visivel mesmo quando herdado de processo oculto
p = subprocess.Popen(cmd, startupinfo=si)
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
