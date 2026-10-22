#!/bin/sh
# Copy the armhf harness and goldens to the Force, check against the goldens and time it there.
set -e
F=root@192.168.1.187
ssh $F 'mkdir -p /tmp/tbt/golden'
scp -q tbtest-arm $F:/tmp/tbt/tbtest
scp -q golden/*.f32 $F:/tmp/tbt/golden/
timeout 600 ssh $F 'cd /tmp/tbt && ./tbtest check golden; for r in 1 2 3; do ./tbtest time | tail -1; done | sort -n -k2 | head -n 1 | sed "s/^/best of 3: /"'
