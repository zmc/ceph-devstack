import os
import subprocess
import yaml

from pathlib import Path
from packaging.version import parse as parse_version, Version
from typing import Dict

from ceph_devstack import logger

"""
The podman info command returns a ton of useful information; we should use
this to rewrite much (all?) of the check_requirements methods.

re: configuring graph driver:
- check store.graphDriverName
  - driver=overlay?
    - check if we can use native or need fuse
      - if we need fuse:
        - check for package; advise install
        - check if we need to set the mount program in conf; advise doing so
  - driver!=overlay?
    - check store.graphRootUsed OR store.graphRoot
      - if dir is not empty, advise removing
    - advise setting graph driver in conf
- anything else??

"""


def get_info() -> Dict:
    out = subprocess.check_output(["podman", "info"])
    return yaml.safe_load(out.decode().strip())


def check_requirements():
    result = True
    podman_info = get_info()
    storage_conf_path = podman_info["store"]["configFile"]
    containers_conf_path = Path(storage_conf_path).parent / "containers.conf"
    host_os = podman_info["host"].get("Os") or podman_info["host"]["os"]
    if host_os.lower() != "linux":
        result = False
        logger.error("Support is currently limited to Linux.")
        return result

    # overlay
    graph_driver = podman_info["store"]["graphDriverName"]
    if graph_driver != "overlay":
        result = False
        logger.error(
            f"The configured graph driver is '{graph_driver}'. "
            f"It must be set to 'overlay' in {storage_conf_path}."
        )
    needs_fuse = False
    # kernel version for native overlay
    kernel_version = Version(podman_info["host"]["kernel"].split("-")[0])
    version_for_overlay = Version("5.12")
    if not kernel_version >= version_for_overlay:
        needs_fuse = True
        logger.warning(
            f"Kernel version ({kernel_version}) is too old to support native rootless overlayfs "
            f"(needs {version_for_overlay})"
        )
    # podman version for native overlay
    podman_version = parse_version(podman_info["version"]["Version"])
    version_for_overlay = Version("3.1")
    if not podman_version >= version_for_overlay:
        needs_fuse = True
        logger.warning(
            "Podman version is too old for rootless native overlayfs"
            f"(needs {version_for_overlay})"
        )
    # fuse-overlayfs presence if not using native overlay
    if needs_fuse:
        try:
            subprocess.check_call(["command", "-v", "fuse-overlayfs"])
        except subprocess.CalledProcessError:
            result = False
            logger.error(
                "Could not find fuse-overlayfs. Try: dnf install fuse-overlayfs"
            )

    # cgroup v2
    if podman_info["host"]["cgroupVersion"] != "v2":
        result = False
        version_for_cgroup = Version("4.15")
        if not kernel_version >= version_for_cgroup:
            logger.error(
                f"Kernel version ({kernel_version}) is too old to support cgroup v2 "
                f"(needs {version_for_cgroup})"
            )
        logger.error(
            "cgroup v2 is not enabled. Try: "
            "grubby --update-kernel=ALL --args='systemd.unified_cgroup_hierarchy=1'"
        )

    # runtime
    runtime = podman_info["host"]["ociRuntime"]["name"]
    if runtime != "crun":
        result = False
        logger.error(
            f"The configured runtime is '{runtime}'. "
            f"It must be set to 'overlay' in {containers_conf_path}. "
            f"Afterward, run 'podman system reset'."
        )

    # SELinux
    result = result and check_selinux_bool("container_manage_cgroup")
    result = result and check_selinux_bool("container_use_devices")

    # podman DNS plugin
    dns_plugin_path = "/usr/libexec/cni/dnsname"
    if not os.path.exists(dns_plugin_path):
        result = False
        logger.error(
            "Could not find the podman DNS plugin. Try: dnf install /usr/libexec/cni/dnsname"
        )

    # sysctl settings for OSD
    result = result and check_sysctl_value("fs.aio-max-nr", 1048576)
    result = result and check_sysctl_value("kernel.pid_max", 4194304)

    return result


def check_selinux_bool(name):
    out = subprocess.check_output(["getsebool", name])
    if out.decode().strip() != f"{name} --> on":
        logger.error(
            f"SELinux boolean '{name}' must be enabled. "
            f"Try: setsebool -P {name}=true"
        )
        return False
    return True


def check_sysctl_value(name: str, min_value: int):
    out = subprocess.check_output(["sysctl", "-b", name])
    current_value = int(out.decode().strip())
    if current_value < min_value:
        logger.error(
            f"sysctl setting {name} ({current_value}) is too low. Try: "
            f"sysctl {name}={min_value}"
        )
