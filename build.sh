#!/bin/sh
# x86 and armhf (Force) builds of the test harness
set -e
SRC="tbtest.cpp voice.cpp oversampler.cpp"
g++ -O3 -std=c++17 $SRC -o tbtest
arm-linux-gnueabihf-g++ -O3 -std=c++17 -march=armv7-a -mfpu=neon-vfpv4 -mfloat-abi=hard -static -Wno-psabi $SRC -o tbtest-arm
