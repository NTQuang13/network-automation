#!/usr/bin/env bash
cd "$(dirname "$0")"
source .venv/bin/activate
P="python main.py"

step()  { clear; printf '\033[1;36m### %s\033[0m\n' "$*"; sleep 2; }
run()   { printf '\n\033[1;32m$ %s\033[0m\n' "$*"; sleep 1; eval "$*"; sleep 3; }
cli()   { docker exec "clab-netauto-$1" Cli -p 15 -c "$2"; }
quiet() { "$@" >/dev/null 2>&1; sleep 5; }

fault_vlan()   { cli acc3 $'configure\nno vlan 40'; }
fault_port()   { cli acc1 $'configure\ninterface Ethernet1\nshutdown'; }

step "1. Backup running-config: tuần tự (-w 1) vs song song (-w 8)"
run "$P backup -w 1"
run "$P backup -w 8"

step "2. Xem trước cấu hình sẽ đẩy (dry-run) trên acc1"
run "$P deploy --template vlan.j2 --vars vars/vlans.yaml -d acc1 --dry-run"

step "3. Triển khai VLAN lên cả 8 thiết bị (tự backup trước khi push)"
run "$P deploy --template vlan.j2 --vars vars/vlans.yaml -w 8"

step "4. So sánh cấu hình trước và sau khi triển khai"
run "$P backup"
run "$P diff -d acc1"

step "5. Giả lập sự cố: acc3 mất VLAN 40, acc1 shutdown cổng uplink"
quiet fault_vlan
quiet fault_port
echo "Đã tạo sự cố, chờ link cập nhật..."

step "6. Thu thập trạng thái, kiểm tra compliance, tạo báo cáo"
run "$P collect"
run "$P compliance"
run "$P report"

step "7. Tự khắc phục: shutdown cổng thừa, đẩy NTP, đẩy lại VLAN cho acc3"
run "$P compliance --fix"
run "$P deploy --template ntp.j2 --vars vars/ntp.yaml"
run "$P deploy --template vlan.j2 --vars vars/vlans.yaml -d acc3"

step "8. Kiểm tra lại: mọi rule PASS và báo cáo mới"
run "$P collect"
run "$P compliance"
run "$P report"

step "9. Rollback acc1 về bản backup đầu tiên"
run "$P rollback -d acc1 -y --file \"\$(ls backups/acc1/*.cfg | head -1)\""

printf '\n\033[1;36m### Hoàn tất\033[0m\n'