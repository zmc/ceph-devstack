#!/bin/bash
set -ex
cd /ceph
rm -rf build
source /opt/rh/gcc-toolset-11/enable
time ./do_cmake.sh
time cmake --build build
