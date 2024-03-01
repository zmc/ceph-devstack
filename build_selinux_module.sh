#!/usr/bin/env bash
set -ex
IMG_NAME=ceph-devstack-selinux
podman build --platform linux/$(uname -m) -t $IMG_NAME -f ceph_devstack/Dockerfile.selinux .
podman create --name $IMG_NAME $IMG_NAME
podman cp $IMG_NAME:/ceph_devstack.pp ./ceph_devstack/
podman rm $IMG_NAME
