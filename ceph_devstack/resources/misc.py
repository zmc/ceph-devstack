from typing import List

from ceph_devstack.resources import PodmanResource


class Network(PodmanResource):
    create_cmd: List[str] = ["podman", "network", "create", "{name}"]
    remove_cmd: List[str] = ["podman", "network", "rm", "{name}"]


class Secret(PodmanResource):
    create_cmd: List[str] = ["podman", "secret", "create", "{name}"]
    remove_cmd: List[str] = ["podman", "secret", "rm", "{name}"]
