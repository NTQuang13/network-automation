import difflib, logging
from pathlib import Path
from netmiko import file_transfer
from .backup import backup_task, clean

log = logging.getLogger("netauto")


def pick_backup(name, file=None):
    if file:
        return Path(file)
    files = sorted(Path("backups", name).glob("*.cfg"))
    if not files:
        raise SystemExit(f"Chưa có backup nào cho {name}")
    return files[-1]      # bản mới nhất = trạng thái trước lần push gần nhất


def _diff(a, b, na, nb):
    return "\n".join(difflib.unified_diff(clean(a), clean(b), fromfile=na, tofile=nb, lineterm=""))


def rollback_task(conn, dev, target, assume_yes=False):
    target = Path(target)
    current = conn.send_command("show running-config")
    diff = _diff(current, target.read_text(), "running-config (hiện tại)", target.name)
    if not diff:
        return "Cấu hình hiện tại đã trùng bản backup, không cần rollback"
    print(diff)
    if not assume_yes and input("\nÁp dụng rollback? [y/N] ").lower() != "y":
        return "Đã huỷ"

    safety = backup_task(conn, dev)               # backup bản hiện tại phòng khi cần quay lại
    log.info("%s: backup an toàn tại %s", dev["name"], safety)

    remote = f"rollback_{dev['name']}.cfg"
    res = file_transfer(conn, source_file=str(target), dest_file=remote,
                        file_system="/mnt/flash", direction="put", overwrite_file=True)
    if not (res["file_exists"] and res["file_verified"]):
        raise RuntimeError(f"Upload file thất bại: {res}")

    out = conn.send_command(f"configure replace flash:{remote}", read_timeout=60)
    log.info("%s: configure replace -> %s", dev["name"], out.strip()[:200])
    conn.send_command("write memory")

    after = _diff(conn.send_command("show running-config"), target.read_text(), "sau rollback", target.name)
    return "Rollback thành công" if not after else f"Còn khác biệt sau rollback:\n{after}"
