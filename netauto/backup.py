import difflib, re
from datetime import datetime
from pathlib import Path

IGNORE = re.compile(r"^! (Command|Time):")

def backup_task(conn, dev):
    cfg = conn.send_command("show running-config")
    folder = Path("backups") / dev["name"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{dev['name']}_{datetime.now():%Y%m%d_%H%M%S}.cfg"
    path.write_text(cfg)
    return str(path)

def _clean(text):
    return [l for l in text.splitlines() if not IGNORE.match(l)]

def diff_latest(name):
    files = sorted(Path("backups", name).glob("*.cfg"))
    if len(files) < 2:
        return "Chưa đủ 2 bản backup"
    old, new = files[-2], files[-1]
    return "\n".join(difflib.unified_diff(
        _clean(old.read_text()), _clean(new.read_text()),
        fromfile=old.name, tofile=new.name, lineterm=""))