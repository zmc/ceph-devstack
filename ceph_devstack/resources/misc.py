from typing import List

from ceph_devstack.resources import PodmanResource


class Network(PodmanResource):
    exists_cmd: List[str] = ["podman", "network", "inspect", "{name}"]
    create_cmd: List[str] = ["podman", "network", "create", "{name}"]
    remove_cmd: List[str] = ["podman", "network", "rm", "{name}"]


class Secret(PodmanResource):
    exists_cmd: List[str] = ["podman", "secret", "inspect", "{name}"]
    create_cmd: List[str] = ["podman", "secret", "create", "{name}"]
    remove_cmd: List[str] = ["podman", "secret", "rm", "{name}"]
