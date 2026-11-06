import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import yaml

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Network Report</title>
<style>
body{{font-family:sans-serif;margin:2em}} table{{border-collapse:collapse;margin-bottom:1.5em}}
th,td{{border:1px solid #ccc;padding:4px 10px}} th{{background:#f0f0f0}}
.bad{{background:#f8d7da}} .ok{{background:#d4edda}}
</style></head><body>
<h1>Network Report</h1><p>Tạo lúc {ts}</p>{body}</body></html>"""

def build_tables(collected, vlans_file, compliance=None):
    expected = {str(v["id"]) for v in yaml.safe_load(open(vlans_file))["vlans"]}
    devices, down, missing = [], [], []
    for r in collected:
        if not r["ok"]:
            devices.append({"device": r["name"], "status": "FAIL", "detail": r["error"]})
            continue
        devices.append({"device": r["name"], "status": "OK", "detail": ""})
        for ifname, i in r["data"]["interfaces"].items():
            if ifname.startswith("Ethernet") and i["linkStatus"] in ("notconnect", "errdisabled"):
                down.append({"device": r["name"], "interface": ifname, "state": i["linkStatus"]})
        for vid in sorted(expected - set(r["data"]["vlans"]), key=int):
            missing.append({"device": r["name"], "missing_vlan": vid})
    tables = {
        "Device Status": pd.DataFrame(devices, columns=["device", "status", "detail"]),
        "Interfaces Down": pd.DataFrame(down, columns=["device", "interface", "state"]),
        "Missing VLANs": pd.DataFrame(missing, columns=["device", "missing_vlan"]),
    }
    if compliance:
        rows = [{"device": r["name"], "rule": c["rule"],
                 "result": "PASS" if c["passed"] else "FAIL", "detail": c["detail"]}
                for r in compliance if r["ok"] for c in r["data"]]
        tables["Compliance"] = pd.DataFrame(rows, columns=["device", "rule", "result", "detail"])
    return tables

def write_reports(tables, outdir="reports"):
    out = Path(outdir); out.mkdir(exist_ok=True)
    with pd.ExcelWriter(out / "report.xlsx", engine="openpyxl") as xw:
        for name, df in tables.items():
            df.to_excel(xw, sheet_name=name, index=False)
    body = ""
    for name, df in tables.items():
        h = df.to_html(index=False, border=0) if len(df) else "<p>Không có dữ liệu (tốt!)</p>"
        h = h.replace("<td>FAIL</td>", '<td class="bad">FAIL</td>').replace("<td>OK</td>", '<td class="ok">OK</td>')
        h = h.replace("<td>PASS</td>", '<td class="ok">PASS</td>')
        body += f"<h2>{name}</h2>{h}"
    (out / "report.html").write_text(HTML.format(ts=datetime.now().strftime("%Y-%m-%d %H:%M:%S"), body=body))

def load_json(path):
    p = Path(path)
    return json.loads(p.read_text()) if p.exists() else None