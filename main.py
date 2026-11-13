import argparse, json, sys, yaml
from pathlib import Path
from netauto.inventory import load_inventory
from netauto.connection import setup_logging, run_parallel, run_on_device


def select(devs, a):
    if a.device:
        devs = [d for d in devs if d["name"] in a.device]
    if a.role:
        devs = [d for d in devs if d.get("role") == a.role]
    if not devs:
        sys.exit("Không có thiết bị nào khớp bộ lọc")
    return devs


def show(results, elapsed):
    for r in sorted(results, key=lambda x: x["name"]):
        status = "OK" if r["ok"] else f"FAIL ({r['error']})"
        print(f"  {r['name']:<8} {status}")
    ok = sum(r["ok"] for r in results)
    print(f"=> {ok}/{len(results)} thành công, {elapsed:.1f}s")


def cmd_backup(a, devs):
    from netauto.backup import backup_task
    res, t = run_parallel(devs, backup_task, workers=a.workers)
    show(res, t)


def cmd_diff(a, devs):
    from netauto.backup import diff_latest
    for d in devs:
        print(f"\n===== {d['name']} =====")
        print(diff_latest(d["name"]) or "Không có thay đổi")


def cmd_deploy(a, devs):
    from netauto.backup import backup_task
    from netauto.deploy import deploy_task
    if not a.dry_run and not a.no_backup:       # luôn backup trước khi push
        res, _ = run_parallel(devs, backup_task, workers=a.workers)
        ok = {r["name"] for r in res if r["ok"]}
        skipped = [d["name"] for d in devs if d["name"] not in ok]
        if skipped:
            print("Bỏ qua (backup lỗi):", skipped)
        devs = [d for d in devs if d["name"] in ok]
    res, t = run_parallel(devs, deploy_task, workers=a.workers,
                          template=a.template, vars_file=a.vars,
                          dry_run=a.dry_run)
    if a.dry_run:
        for r in sorted(res, key=lambda x: x["name"]):
            print(f"\n--- {r['name']} ---")
            print("\n".join(r["data"]) if r["ok"] else r["error"])
    show(res, t)


def cmd_collect(a, devs):
    from netauto.collect import collect_task, save_snapshot
    res, t = run_parallel(devs, collect_task, workers=a.workers)
    show(res, t)
    print("Đã lưu:", save_snapshot(res))


def cmd_report(a, devs):
    from netauto.report import generate
    vlans = yaml.safe_load(open("vars/vlans.yaml"))["vlans"]
    print("Đã tạo:", *generate({v["id"] for v in vlans}))


def cmd_compliance(a, devs):
    from netauto.compliance import compliance_task, remediate_task
    rules = yaml.safe_load(open(a.rules))["rules"]
    res, t = run_parallel(devs, compliance_task, workers=a.workers, rules=rules)
    rows = [row for r in res if r["ok"] for row in r["data"]]
    Path("data").mkdir(exist_ok=True)
    Path("data/compliance.json").write_text(json.dumps(rows, indent=2))
    for row in rows:
        print(f"  {row['device']:<8} {row['status']:<5} {row['rule']}  {row['detail']}")
    show(res, t)
    if a.fix:
        res, t = run_parallel(devs, remediate_task, workers=a.workers)
        show(res, t)


def cmd_rollback(a, devs):
    from netauto.rollback import pick_backup, rollback_task
    if len(devs) != 1:
        sys.exit("Rollback chỉ chạy trên 1 thiết bị: dùng -d <tên>")
    dev = devs[0]
    target = pick_backup(dev["name"], a.file)
    print("Rollback về:", target)
    r = run_on_device(dev, rollback_task, target=str(target), assume_yes=a.yes)
    print(r["data"] if r["ok"] else f"FAIL: {r['error']}")


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-i", "--inventory", default="inventory/devices.yaml")
    common.add_argument("-d", "--device", nargs="+", help="chỉ chạy trên các thiết bị này")
    common.add_argument("--role", help="lọc theo role: core/access/edge")
    common.add_argument("-w", "--workers", type=int, default=10)

    p = argparse.ArgumentParser(description="Network Automation Tool")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup", parents=[common])
    sub.add_parser("diff", parents=[common])
    s = sub.add_parser("deploy", parents=[common])
    s.add_argument("--template", required=True)
    s.add_argument("--vars", required=True)
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--no-backup", action="store_true")
    sub.add_parser("collect", parents=[common])
    sub.add_parser("report", parents=[common])
    s = sub.add_parser("compliance", parents=[common])
    s.add_argument("--rules", default="rules/compliance.yaml")
    s.add_argument("--fix", action="store_true", help="tự khắc phục vi phạm")
    s = sub.add_parser("rollback", parents=[common])
    s.add_argument("--file", help="bản backup cần quay về (mặc định: bản mới nhất)")
    s.add_argument("-y", "--yes", action="store_true")

    a = p.parse_args()
    Path("logs").mkdir(exist_ok=True)
    setup_logging()
    devs = select(load_inventory(a.inventory), a)
    globals()[f"cmd_{a.cmd}"](a, devs)


if __name__ == "__main__":
    main()
