import argparse, json
from netauto.inventory import load_inventory
from netauto.connection import setup_logging, run_parallel
from netauto.backup import backup_task, diff_latest
from netauto.deploy import deploy_task

def main():
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--inventory", default="inventory/devices.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("backup")
    d = sub.add_parser("diff");   d.add_argument("device")
    x = sub.add_parser("deploy")
    x.add_argument("--template", required=True)
    x.add_argument("--vars", required=True)
    x.add_argument("--dry-run", action="store_true")
    x.add_argument("--no-backup", action="store_true")
    a = p.parse_args()

    setup_logging()
    devs = load_inventory(a.inventory)

    if a.cmd == "backup":
        res, t = run_parallel(devs, backup_task)
    elif a.cmd == "diff":
        print(diff_latest(a.device)); return
    elif a.cmd == "deploy":
        if not a.dry_run and not a.no_backup:
            run_parallel(devs, backup_task)          # luôn backup trước khi push
        res, t = run_parallel(devs, deploy_task, template=a.template,
                              vars_file=a.vars, dry_run=a.dry_run)
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print(f"Thời gian: {t:.1f}s")

if __name__ == "__main__":
    main()