import json
from datetime import datetime
from pathlib import Path
import pandas as pd
from jinja2 import Environment, FileSystemLoader


def build_frames(snap, expected_vlans):
    t = snap["tables"]
    dev = pd.DataFrame(snap["devices"])
    dev["status"] = dev["ok"].map({True: "OK", False: "FAIL"})
    dev_tbl = dev[["name", "status", "error"]]

    intf = pd.DataFrame(t["interfaces"], columns=["device", "interface", "status", "description", "vlan"])
    down = intf[(intf["status"] != "connected")
                & ~intf["interface"].astype(str).str.startswith("Management")]

    vl = pd.DataFrame(t["vlans"], columns=["device", "vlan_id", "name", "status"])
    rows = []
    for d in dev.loc[dev["ok"], "name"]:
        have = set(vl.loc[vl["device"] == d, "vlan_id"])
        rows += [{"device": d, "missing_vlan": v} for v in sorted(expected_vlans - have)]
    missing = pd.DataFrame(rows, columns=["device", "missing_vlan"])
    return dev_tbl, down, missing


def generate(expected_vlans):
    snap = json.loads(Path("data/latest.json").read_text())
    dev, down, missing = build_frames(snap, expected_vlans)
    frames = [("Trạng thái thiết bị", "Device Status", dev),
              ("Cổng không connected", "Interfaces Down", down),
              ("VLAN còn thiếu", "Missing VLANs", missing)]
    comp_file = Path("data/compliance.json")
    if comp_file.exists():
        frames.append(("Compliance", "Compliance", pd.DataFrame(json.loads(comp_file.read_text()))))

    Path("reports").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    xlsx, html = f"reports/report_{ts}.xlsx", f"reports/report_{ts}.html"

    with pd.ExcelWriter(xlsx, engine="openpyxl") as w:
        for _, sheet, df in frames:
            df.to_excel(w, sheet_name=sheet, index=False)

    def to_html(df):
        h = df.fillna("").to_html(index=False, classes="tbl", border=0)
        for word, cls in (("FAIL", "bad"), ("PASS", "good"), ("OK", "good"), ("notconnect", "bad")):
            h = h.replace(f"<td>{word}</td>", f'<td class="{cls}">{word}</td>')
        return h

    env = Environment(loader=FileSystemLoader("templates"))
    Path(html).write_text(env.get_template("report.html.j2").render(
        ts=ts, total=len(snap["devices"]),
	failed=sum(1 for d in snap["devices"] if not d["ok"]),
        sections=[(title, to_html(df)) for title, _, df in frames]))
    return xlsx, html
