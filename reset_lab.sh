#!/usr/bin/env bash
cd "$(dirname "$0")"

ports() {   # số cổng Ethernet trên mỗi node
  case $1 in core*) echo 4;; acc*) echo 1;; edge*) echo 2;; esac
}

for n in core1 core2 acc1 acc2 acc3 acc4 edge1 edge2; do
  {
    echo "configure"
    echo "username admin privilege 15 role network-admin"
    echo "no vlan 10,20,30,40"
    echo "no ntp server 172.20.20.1"
    for i in $(seq 1 "$(ports $n)"); do
      echo "interface Ethernet$i"
      echo "no shutdown"
    done
    echo "end"
    echo "write memory"
  } | docker exec -i clab-netauto-$n Cli -p 15 >/dev/null 2>&1
  echo "$n: đã reset"
done

rm -rf backups data reports
: > logs/netauto.log