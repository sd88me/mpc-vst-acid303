#!/bin/sh
# Copy the armhf harness and goldens to the Force, check against the goldens and time it there.
set -e
F=root@192.168.1.187
ssh $F 'mkdir -p /tmp/tbt/golden'
scp -q tbtest-arm $F:/tmp/tbt/tbtest
scp -q golden/*.f32 $F:/tmp/tbt/golden/
timeout 300 ssh $F 'cd /tmp/tbt && ./tbtest check golden; ./tbtest time'
