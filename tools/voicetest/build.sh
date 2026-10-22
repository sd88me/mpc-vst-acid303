#!/bin/sh
# x86 and armhf (Force) builds of the voice test harness, into tools/voicetest/.
set -e
cd "$(dirname "$0")"
L=../../src/lemus
SRC="tbtest.cpp $L/voice.cpp $L/oversampler.cpp"
g++ -O3 -std=c++17 -I$L $SRC -o tbtest
arm-linux-gnueabihf-g++ -O3 -std=c++17 -mcpu=cortex-a17 -ffast-math -fno-finite-math-only -mfpu=neon-vfpv4 -mfloat-abi=hard -static -Wno-psabi -I$L $SRC -o tbtest-arm
