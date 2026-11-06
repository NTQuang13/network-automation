import json
import logging
from pathlib import Path
import pandas as pd

log = logging.getLogger("netauto")

TEXT_CMDS = {
    "arp": "show ip arp",
    "mac": "show mac address-table",
    "routes": "show ip route",
}

# --- Chuyển JSON của EOS về list[dict] phẳng (dùng khi TextFSM lỗi) ---
def _flatten_arp(j):
    return [{"ip": e.get("address"), "mac": e.get("hwAddress"),
             "interface": e.get("interface"), "age": e.get("age")}
            for e in j.get("ipV4Neighbors", [])]

def _flatten_mac(j):
    return [{"vlan": e.get("vlanId"), "mac": e.get("macAddress"),
             "type": e.get("entryType"), "interface": e.get("interface")}
            for e in j.get("unicastTable", {}).get("tableEntries", [])]

def _flatten_routes(j):
    rows = []
    for vrf, v in j.get("vrfs", {}).items():
        for prefix, r in v.get("routes", {}).items():
            vias = r.get("vias") or [{}]
            for via in vias:
                rows.append({"vrf": vrf, "prefix": prefix, "type": r.get("routeType"),
                             "next_hop": via.get("nexthopAddr"),
                             "interface": via.get("interface")})
    return rows

FLATTEN = {"arp": _flatten_arp, "mac": _flatten_mac, "routes": _flatten_routes}

def _run_text_cmd(conn, key, cmd, dev_name):
    # 1) TextFSM
    try:
        out = conn.send_command(cmd, use_textfsm=True)
        if isinstance(out, list):
            return out
    except Exception as e:
        log.warning("%s: TextFSM lỗi cho '%s' (%s), chuyển sang JSON", dev_name, cmd, e)
    # 2) JSON gốc của EOS
    try:
        j = json.loads(conn.send_command(cmd + " | json"))
        return FLATTEN[key](j)
    except Exception as e:
        log.warning("%s: JSON lỗi cho '%s' (%s), lưu text thô", dev_name, cmd, e)
    # 3) Text thô
    return {"raw": conn.send_command(cmd)}

def collect_task(conn, dev):
    data = {
        "interfaces": json.loads(conn.send_command("show interfaces status | json"))["interfaceStatuses"],
        "vlans": json.loads(conn.send_command("show vlan | json"))["vlans"],
    }
    for key, cmd in TEXT_CMDS.items():
        data[key] = _run_text_cmd(conn, key, cmd, dev["name"])
    return data

def save_collected(results, outdir="reports"):
    out = Path(outdir)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "collected.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    for r in results:
        if not r["ok"]:
            continue
        for key in TEXT_CMDS:
            rows = r["data"][key]
            if isinstance(rows, list) and rows:
                pd.DataFrame(rows).to_csv(out / "data" / f"{r['name']}_{key}.csv", index=False)