import re
from .collect import run_show, normalize


def check_rules(rules, cfg, intf_rows, name):
    """Hàm thuần (không cần kết nối) nên dễ viết unit test."""
    out = []
    for r in rules:
        if r.get("type") == "interface_unused_shutdown":
            # notconnect = cổng admin-up nhưng không có link; "disabled" = đã shutdown
            bad = [i["interface"] for i in intf_rows if i["status"] == "notconnect"]
            ok, detail = not bad, ", ".join(bad)
        elif "must_contain" in r:
            ok = re.search(r["must_contain"], cfg, re.M) is not None
            detail = "" if ok else f"thiếu: {r['must_contain']}"
        elif "must_not_contain" in r:
            ok = re.search(r["must_not_contain"], cfg, re.M) is None
            detail = "" if ok else f"vi phạm: {r['must_not_contain']}"
        else:
            continue
        out.append({"device": name, "rule": r["name"],
                    "status": "PASS" if ok else "FAIL", "detail": detail})
    return out


def compliance_task(conn, dev, rules):
    cfg = conn.send_command("show running-config")
    rows = normalize("interfaces", run_show(conn, dev, "show interfaces status"), dev["name"])
    return check_rules(rules, cfg, rows, dev["name"])


def remediate_task(conn, dev):
    """Shutdown tất cả cổng notconnect."""
    rows = normalize("interfaces", run_show(conn, dev, "show interfaces status"), dev["name"])
    ports = [r["interface"] for r in rows if r["status"] == "notconnect"]
    if not ports:
        return "Không có gì cần sửa"
    cmds = [x for p in ports for x in (f"interface {p}", "shutdown")]
    conn.send_config_set(cmds)
    conn.save_config()
    return f"Đã shutdown: {', '.join(ports)}"
