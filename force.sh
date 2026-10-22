#!/bin/sh
# Copy the armhf harness and goldens to the Force, check against the goldens and time it there:
# best of 5, pinned to core 3 (MPC runs alongside), with the core's clock and temperature after.
set -e
F=root@192.168.1.187
ssh $F 'mkdir -p /tmp/tbt/golden'
scp -q tbtest-arm $F:/tmp/tbt/tbtest
scp -q golden/*.f32 $F:/tmp/tbt/golden/
timeout 900 ssh $F 'cd /tmp/tbt && ./tbtest check golden
for r in 1 2 3 4 5; do taskset -c 3 ./tbtest time | tail -n 1; done | sort -n -k2 | head -n 1 | sed "s/^/best of 5 (core 3): /"
echo "cpu3 $(cat /sys/devices/system/cpu/cpu3/cpufreq/scaling_cur_freq) kHz, $(cat /sys/class/thermal/thermal_zone0/temp) mC"'
