from pathlib import Path
import difflib
from netauto.backup import _clean


def _diff(a, b, fa, fb):
    return "\n".join(difflib.unified_diff(_clean(a), _clean(b),
                                          fromfile=fa, tofile=fb, lineterm=""))


def _blocks(cfg):
    """Tách config thành {dòng đầu khối: [các dòng con]} (chỉ khối cấp cao nhất)."""
    blocks, cur = {}, None
    for line in cfg.splitlines():
        if not line.strip() or line.startswith("!"):
            cur = None
        elif not line.startswith(" "):
            cur = line.strip()
            blocks[cur] = []
        elif cur:
            blocks[cur].append(line.strip())
    return blocks


def rollback_task(conn, dev, target_name, dry_run=True):
    target = Path("backups", dev["name"], target_name)
    if not target.exists():
        raise FileNotFoundError(f"Không thấy file {target}")

    current = conn.send_command("show running-config")
    want = target.read_text()
    diff = _diff(current, want, "hiện tại", target.name)

    cur_b, want_b = _blocks(current), _blocks(want)

    # Khối có trên thiết bị nhưng không có trong bản đích -> xóa (chỉ làm với VLAN)
    remove = [h for h in cur_b if h not in want_b]
    remove_vlan = [h for h in remove if h.startswith("vlan ")]
    skipped = [h for h in remove if h not in remove_vlan]

    # Khối có trong bản đích nhưng khác hiện tại -> gửi lại
    add = [h for h in want_b if cur_b.get(h) != want_b[h]]

    plan = [f"no {h}" for h in remove_vlan]
    for h in add:
        plan.append(h)
        plan.extend(want_b[h])

    result = {"file": target.name, "diff": diff, "commands": plan,
              "skipped_manual": skipped, "applied": False}
    if dry_run or not plan:
        return result

    conn.enable()
    conn.send_config_set(plan)
    conn.save_config()

    after = conn.send_command("show running-config")
    result["applied"] = True
    result["remaining_diff"] = _diff(after, want, "sau rollback", target.name)
    return result