import json
from datetime import datetime
from pathlib import Path
import pandas as pd

COMMANDS = {
    "interfaces": "show interfaces status",
    "vlans": "show vlan",
    "arp": "show ip arp",
    "mac": "show mac address-table",
    "routes": "show ip route",
}


def run_show(conn, dev, cmd):
    if dev["device_type"] == "arista_eos":
        return json.loads(conn.send_command(cmd + " | json", read_timeout=30))
    return conn.send_command(cmd, use_textfsm=True, read_timeout=30)


def normalize(kind, raw, name):
    """Đưa output về list[dict] phẳng, thêm cột device."""
    if isinstance(raw, list):                     # kết quả TextFSM
        return [{"device": name, **r} for r in raw]
    rows = []
    if kind == "interfaces":
        for ifn, v in raw.get("interfaceStatuses", {}).items():
            rows.append({"interface": ifn, "status": v.get("linkStatus"),
                         "description": v.get("description", ""),
                         "vlan": v.get("vlanInformation", {}).get("vlanId")})
    elif kind == "vlans":
        for vid, v in raw.get("vlans", {}).items():
            rows.append({"vlan_id": int(vid), "name": v.get("name"),
                         "status": v.get("status")})
    elif kind == "arp":
        for n in raw.get("ipV4Neighbors", []):
            rows.append({"ip": n.get("address"), "mac": n.get("hwAddress"),
                         "interface": n.get("interface")})
    elif kind == "mac":
        for e in raw.get("unicastTable", {}).get("tableEntries", []):
            rows.append({"vlan": e.get("vlanId"), "mac": e.get("macAddress"),
                         "interface": e.get("interface"), "type": e.get("entryType")})
    elif kind == "routes":
        for prefix, r in raw.get("vrfs", {}).get("default", {}).get("routes", {}).items():
            via = (r.get("vias") or [{}])[0]
            rows.append({"prefix": prefix, "type": r.get("routeType"),
                         "next_hop": via.get("nexthopAddr", ""),
                         "interface": via.get("interface", "")})
    return [{"device": name, **r} for r in rows]


def collect_task(conn, dev):
    data = {}
    for kind, cmd in COMMANDS.items():
        try:
            data[kind] = normalize(kind, run_show(conn, dev, cmd), dev["name"])
        except Exception as e:                    # 1 lệnh lỗi không làm hỏng cả thiết bị
            data[kind] = []
    return data


def save_snapshot(results):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path("data") / ts
    out.mkdir(parents=True, exist_ok=True)
    snap = {"timestamp": ts, "devices": [], "tables": {k: [] for k in COMMANDS}}
    for r in results:
        snap["devices"].append({"name": r["name"], "ok": r["ok"],
                                "error": r.get("error", "")})
        if r["ok"]:
            for kind, rows in r["data"].items():
                snap["tables"][kind].extend(rows)
    text = json.dumps(snap, indent=2, default=str)
    (out / "snapshot.json").write_text(text)
    Path("data/latest.json").write_text(text)
    for kind, rows in snap["tables"].items():
        pd.DataFrame(rows).to_csv(out / f"{kind}.csv", index=False)
    return out
