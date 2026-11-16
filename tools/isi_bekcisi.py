"""Heat and memory watchdog for the live bench. Runs beside the measurement runs and reads the machine once a minute.

    python tools/isi_bekcisi.py                 # runs until stopped (create results/saha/durum/BEKCI_DUR to end it)

What it reads: GPU temperature and load (nvidia-smi), CPU load and free memory (WMI). The CPU's own temperature
cannot be read on this PC without administrator rights, so CPU load is capped instead and the GPU temperature (the
same cooling loop on a laptop) is the thermal signal.

What it does, through two files the runner honours (vardiya/saha/kosu.py and ajan.py):
    results/saha/durum/BEKLE   every run pauses before its next step while this file exists (cool down)
    results/saha/durum/DUR     every run stops before its next episode (emergency); local models are unloaded

One line per minute goes to results/saha/durum/isi.log; a line is printed only when the state changes.
"""
import ctypes
import datetime
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
DURUM = pathlib.Path(os.environ["SAHA_SONUC"]) / "durum" if os.environ.get("SAHA_SONUC") else ROOT / "results" / "saha" / "durum"
BEKLE, DUR, BEKCI_DUR, LOG = DURUM / "BEKLE", DURUM / "DUR", DURUM / "BEKCI_DUR", DURUM / "isi.log"

# pause above these, resume below those (two calm minutes in a row); stop everything above the last ones
GPU_BEKLE, GPU_DEVAM, GPU_DUR = 76, 66, 84          # degrees C
CPU_BEKLE, CPU_DEVAM = 70, 45                       # percent load, two minutes in a row to pause
RAM_BEKLE, RAM_DEVAM, RAM_DUR = 3.0, 4.0, 1.5       # GB free


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong), ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong), ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]


def bellek():
    """(free physical GB, free commit GB)"""
    m = MEMORYSTATUSEX()
    m.dwLength = ctypes.sizeof(m)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    return m.ullAvailPhys / 2 ** 30, m.ullAvailPageFile / 2 ** 30


def gpu():
    """(temperature C, load %, memory MB) or (None, None, None) when nvidia-smi does not answer."""
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu,memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=20).stdout.strip().splitlines()[0]
        t, u, m = (int(x.strip()) for x in out.split(","))
        return t, u, m
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return None, None, None


def cpu():
    """CPU load in percent, averaged over the processor packages; None when WMI does not answer."""
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average"],
                             capture_output=True, text=True, timeout=40).stdout.strip()
        return float(out.replace(",", "."))
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def karar(olcum, durum):
    """The next state ('calis', 'bekle', 'dur') and the reason, from one reading and the running counters.
    `durum` carries {"hal", "sicak", "serin"}: the current state and how many minutes in a row were hot or calm."""
    t, yuk, ram = olcum["gpu_c"], olcum["cpu"], olcum["ram"]
    if (t is not None and t >= GPU_DUR) or ram < RAM_DUR:
        return "dur", f"acil: gpu {t} C, bos bellek {ram:.1f} GB"
    sicak = (t is not None and t >= GPU_BEKLE) or ram < RAM_BEKLE
    yuklu = yuk is not None and yuk >= CPU_BEKLE
    durum["sicak"] = durum["sicak"] + 1 if (sicak or yuklu) else 0
    serin = (t is None or t <= GPU_DEVAM) and (yuk is None or yuk <= CPU_DEVAM) and ram >= RAM_DEVAM
    durum["serin"] = durum["serin"] + 1 if serin else 0
    if durum["hal"] == "calis":
        if sicak or durum["sicak"] >= 2:          # heat and memory pause at once; CPU load needs two minutes
            return "bekle", f"gpu {t} C, islemci %{yuk}, bos bellek {ram:.1f} GB"
        return "calis", ""
    if durum["serin"] >= 2:
        return "calis", f"sogudu: gpu {t} C, islemci %{yuk}, bos bellek {ram:.1f} GB"
    return durum["hal"], ""


def modelleri_bosalt():
    """Unload local models from every Ollama server this bench may have used (frees the GPU)."""
    for host in ("127.0.0.1:11434", "127.0.0.1:11435"):
        try:
            ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=20, env={**os.environ, "OLLAMA_HOST": host}).stdout
            for line in ps.splitlines()[1:]:
                name = line.split()[0] if line.split() else ""
                if name:
                    subprocess.run(["ollama", "stop", name], capture_output=True, timeout=30, env={**os.environ, "OLLAMA_HOST": host})
        except (OSError, subprocess.TimeoutExpired):
            pass


def main(aralik=60):
    DURUM.mkdir(parents=True, exist_ok=True)
    durum = {"hal": "bekle" if BEKLE.exists() else "calis", "sicak": 0, "serin": 0}
    print(f"isi bekcisi basladi: her {aralik} sn; gpu bekle>={GPU_BEKLE} devam<={GPU_DEVAM} dur>={GPU_DUR}; "
          f"islemci bekle>=%{CPU_BEKLE}; bellek bekle<{RAM_BEKLE} GB", flush=True)
    while not BEKCI_DUR.exists():
        t, u, m = gpu()
        ram, commit = bellek()
        olcum = {"gpu_c": t, "gpu_yuk": u, "gpu_mb": m, "cpu": cpu(), "ram": ram, "commit": commit}
        yeni, neden = karar(olcum, durum)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{now} gpu={t}C %{u} {m}MB islemci=%{olcum['cpu']} bos_bellek={ram:.1f}GB bos_taahhut={commit:.1f}GB hal={yeni}\n")
        if yeni != durum["hal"]:
            if yeni == "bekle":
                BEKLE.write_text(f"{now} {neden}\n", encoding="utf-8")
            elif yeni == "dur":
                DUR.write_text(f"{now} isi bekcisi: {neden}\n", encoding="utf-8")
                BEKLE.write_text(f"{now} {neden}\n", encoding="utf-8")
                modelleri_bosalt()
            elif yeni == "calis":
                BEKLE.unlink(missing_ok=True)       # DUR is never removed here: a person or the orchestrator does that
            print(f"{now} {durum['hal']} -> {yeni}: {neden}", flush=True)
            durum["hal"], durum["sicak"], durum["serin"] = yeni, 0, 0
        time.sleep(aralik)
    BEKCI_DUR.unlink(missing_ok=True)
    print("isi bekcisi durduruldu", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 60))
