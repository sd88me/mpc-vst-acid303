#!/bin/sh
# Sampling profile on the Force: per source line (with inlining) and per function.
set -e
: "${FORCE:?set FORCE=root@<force ip>}"
T=${TMPDIR:-/tmp}
arm-linux-gnueabihf-g++ -O3 -g -std=c++17 -mcpu=cortex-a17 -ffast-math -fno-finite-math-only -mfpu=neon-vfpv4 -mfloat-abi=hard -static -Wno-psabi -I../../src/lemus tbtest.cpp ../../src/lemus/voice.cpp ../../src/lemus/oversampler.cpp pcprof.cpp -o $T/tbpc
scp -q $T/tbpc $FORCE:/tmp/tbt/tbpc
timeout 300 ssh $FORCE "cd /tmp/tbt && $PROFENV ./tbpc time >/dev/null && cat pcprof.txt" > $T/pcprof.txt
awk '{print $2}' $T/pcprof.txt | arm-linux-gnueabihf-addr2line -f -C -e $T/tbpc | paste - - > $T/pcsym.txt
paste -d' ' $T/pcprof.txt $T/pcsym.txt > $T/pcall.txt
TOTAL=$(awk '{s+=$1} END {print s}' $T/pcall.txt)
echo "== by function ($TOTAL samples)"
awk -v t=$TOTAL '{f=$3; c[f]+=$1} END {for (k in c) printf "%5.1f%% %s\n", 100*c[k]/t, k}' $T/pcall.txt | sort -rn | head -${1:-15}
echo "== by line"
awk -v t=$TOTAL '{n=split($NF,a,"/"); l=a[n]; sub(/ .*/,"",l); c[l]+=$1} END {for (k in c) printf "%5.1f%% %s\n", 100*c[k]/t, k}' $T/pcall.txt | sort -rn | head -${2:-30}
