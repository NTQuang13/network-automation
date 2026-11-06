import argparse, json
from netauto.inventory import load_inventory
from netauto.connection import setup_logging, run_parallel
from netauto.backup import backup_task, diff_latest
from netauto.deploy import deploy_task
from netauto.collect import collect_task, save_collected
from netauto.compliance import compliance_task
from netauto.rollback import rollback_task
from netauto import report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--inventory", default="inventory/devices.yaml")
    p.add_argument("-d", "--devices", type=lambda s: s.split(","), help="chỉ chạy trên các thiết bị này")
    p.add_argument("--workers", type=int, default=8)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup")
    s = sub.add_parser("diff"); s.add_argument("device")
    s = sub.add_parser("deploy")
    s.add_argument("--template", required=True); s.add_argument("--vars", required=True)
    s.add_argument("--dry-run", action="store_true"); s.add_argument("--no-backup", action="store_true")
    sub.add_parser("collect")
    s = sub.add_parser("report"); s.add_argument("--vlans", default="vars/vlans.yaml")
    s = sub.add_parser("compliance")
    s.add_argument("--rules", default="vars/compliance.yaml"); s.add_argument("--fix", action="store_true")
    s = sub.add_parser("rollback")
    s.add_argument("--steps", type=int, default=1); s.add_argument("--yes", action="store_true")
    s.add_argument("--to", required=True, help="tên file backup cần quay về")
    a = p.parse_args()

    setup_logging()
    devs = load_inventory(a.inventory)
    if a.devices:
        devs = [d for d in devs if d["name"] in a.devices]
    W = a.workers

    if a.cmd == "diff":
        print(diff_latest(a.device)); return

    if a.cmd == "backup":
        res, t = run_parallel(devs, backup_task, workers=W)

    elif a.cmd == "deploy":
        if not a.dry_run and not a.no_backup:
            run_parallel(devs, backup_task, workers=W)
        res, t = run_parallel(devs, deploy_task, workers=W, template=a.template,
                              vars_file=a.vars, dry_run=a.dry_run)

    elif a.cmd == "collect":
        res, t = run_parallel(devs, collect_task, workers=W)
        save_collected(res)
        print(f"Đã lưu reports/collected.json và CSV trong reports/data/")
        res = [{"name": r["name"], "ok": r["ok"], "error": r.get("error")} for r in res]

    elif a.cmd == "report":
        collected = report.load_json("reports/collected.json")
        if not collected:
            print("Chưa có dữ liệu, chạy 'collect' trước"); return
        tables = report.build_tables(collected, a.vlans, report.load_json("reports/compliance.json"))
        report.write_reports(tables)
        print("Đã tạo reports/report.html và reports/report.xlsx"); return

    elif a.cmd == "compliance":
        res, t = run_parallel(devs, compliance_task, workers=W, rules_file=a.rules, fix=a.fix)
        json.dump(res, open("reports/compliance.json", "w"), indent=2, ensure_ascii=False)
        for r in res:
            if not r["ok"]:
                print(f"{r['name']}: LỖI {r['error']}"); continue
            for c in r["data"]:
                print(f"{r['name']:8} {'PASS' if c['passed'] else 'FAIL'}  {c['rule']}  {c['detail']}")
        print(f"Thời gian: {t:.1f}s"); return

    elif a.cmd == "rollback":
        res, _ = run_parallel(devs, rollback_task, workers=W, target_name=a.to, dry_run=True)
        for r in res:
            print(f"\n=== {r['name']} ===")
            print(f"LỖI: {r['error']}" if not r["ok"] else (r["data"]["diff"] or "(không có khác biệt)"))

        if not any(r["ok"] and r["data"]["diff"] for r in res):
            print("\nKhông có thay đổi nào cần rollback"); return

        if not a.yes and input("\nGõ 'yes' để rollback: ").strip() != "yes":
            print("Đã hủy"); return

        run_parallel(devs, backup_task, workers=W)   # lưu trạng thái hiện tại trước khi đổi
        res, t = run_parallel(devs, rollback_task, workers=W, target_name=a.to, dry_run=False)

    print(json.dumps(res, indent=2, ensure_ascii=False))
    print(f"Thời gian: {t:.1f}s")

if __name__ == "__main__":
    main()