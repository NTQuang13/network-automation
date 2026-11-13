#!/usr/bin/env bash
for n in core1 core2 acc1 acc2 acc3 acc4 edge1 edge2; do
  printf 'configure\nusername admin privilege 15 role network-admin\naaa authorization exec default local\nend\nwrite memory\n' \
    | docker exec -i clab-netauto-$n Cli -p 15 >/dev/null
  echo "$n: đã cấp privilege 15 + bật exec authorization"
done