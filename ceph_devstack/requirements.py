import json
import os

from packaging.version import parse as parse_version, Version

from ceph_devstack import Config, logger
from ceph_devstack.util import async_cmd


async def check_requirements():
    result = True
    uname_result = os.uname()
    if uname_result.sysname.lower() != "linux":
        result = False
        logger.error("Support is currently limited to Linux.")
        return result
    proc = await async_cmd(["sudo", "-v"])
    if proc.returncode:
        result = False
        logger.error("sudo access is required")
    needs_fuse = False
    # kernel version for native overlay
    kernel_version = parse_version(uname_result.release.split("-")[0])
    version_for_overlay = Version("5.12")
    if not kernel_version >= version_for_overlay:
        needs_fuse = True
        logger.warning(
            f"Kernel version ({kernel_version}) is too old to support native rootless overlayfs "
            f"(needs {version_for_overlay})"
        )
    # podman version for native overlay
    proc = await async_cmd(["podman", "version", "-f", "json"])
    podman_version = parse_version(
        json.loads((await proc.stdout.read()).decode())["Client"]["Version"]
    )
    version_for_overlay = Version("3.1")
    if not podman_version >= version_for_overlay:
        needs_fuse = True
        logger.warning(
            "Podman version is too old for rootless native overlayfs"
            f"(needs {version_for_overlay})"
        )
    if needs_fuse:
        Config.native_overlayfs = False
        proc = await async_cmd(["command", "-v", "fuse-overlayfs"])
        if proc and proc.returncode:
            result = False
            logger.error(
                "Could not find fuse-overlayfs. Try: dnf install fuse-overlayfs"
            )
    # cgroup v2
    version_for_cgroup = Version("4.15")
    if not kernel_version >= version_for_cgroup:
        logger.warning(
            f"Kernel version ({kernel_version}) is too old to support cgroup v2 "
            f"(needs {version_for_cgroup})"
        )
    if not os.path.exists("/sys/fs/cgroup/cgroup.controllers"):
        logger.warning(
            "cgroup v2 is not enabled. Try: "
            "grubby --update-kernel=ALL --args='systemd.unified_cgroup_hierarchy=1'"
        )
    # podman DNS plugin
    dns_plugin_path = "/usr/libexec/cni/dnsname"
    proc = await async_cmd(["ls", dns_plugin_path])
    if proc.returncode:
        result = False
        logger.error(
            "Could not find the podman DNS plugin. Try: dnf install /usr/libexec/cni/dnsname"
        )
    return result
