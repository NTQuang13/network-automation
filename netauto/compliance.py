import json
import yaml

def parse_interface_blocks(cfg):
    blocks, cur = {}, None
    for line in cfg.splitlines():
        if line.startswith("interface "):
            cur = line.split(None, 1)[1]
            blocks[cur] = []
        elif cur and line.startswith("   "):
            blocks[cur].append(line.strip())
        else:
            cur = None
    return blocks

def compliance_task(conn, dev, rules_file, fix=False):
    rules = yaml.safe_load(open(rules_file))["rules"]
    cfg = conn.send_command("show running-config")
    blocks = parse_interface_blocks(cfg)
    status = json.loads(conn.send_command("show interfaces status | json"))["interfaceStatuses"]
    results, unused = [], []
    for r in rules:
        if r.get("type") == "interface_unused_shutdown":
            unused = [n for n, i in status.items()
                      if n.startswith("Ethernet") and i["linkStatus"] == "notconnect"
                      and "shutdown" not in blocks.get(n, [])]
            results.append({"rule": r["name"], "passed": not unused, "detail": ", ".join(unused)})
        elif "must_contain" in r:
            ok = r["must_contain"] in cfg
            results.append({"rule": r["name"], "passed": ok, "detail": "" if ok else "thiếu: " + r["must_contain"]})
        elif "must_not_contain" in r:
            ok = r["must_not_contain"] not in cfg
            results.append({"rule": r["name"], "passed": ok, "detail": "" if ok else "có: " + r["must_not_contain"]})
    if fix and unused:
        cmds = [c for n in unused for c in (f"interface {n}", "shutdown")]
        conn.send_config_set(cmds)
        conn.save_config()
        for res in results:
            if res["detail"] == ", ".join(unused):
                res.update(passed=True, detail="đã tự sửa: " + res["detail"])
    return results