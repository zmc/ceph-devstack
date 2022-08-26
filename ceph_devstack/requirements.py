import json

from ceph_devstack import Config, logger
from ceph_devstack.util import async_cmd


async def check_requirements():
    result = True
    proc = await async_cmd(["uname", "-s"])
    if proc:
        assert proc.stdout is not None
        kname = (await proc.stdout.read()).decode().strip().lower()
        if kname != "linux":
            result = False
            logger.error("Support is currently limited to Linux.")
            return result
    proc = await async_cmd(["sudo", "-v"])
    if proc and proc.returncode:
        result = False
        logger.error("sudo access is required")
    needs_fuse = False
    # kernel version for native overlay
    proc = await async_cmd(["uname", "-r"])
    if proc:
        assert proc.stdout is not None
        version_str = (await proc.stdout.read()).decode()
        major, minor = version_str.split(".")[:2]
        if not (int(major) >= 5 and int(minor) >= 12):
            needs_fuse = True
            logger.warning("Kernel version is too old for rootless native overlayfs")
    # podman version for native overlay
    proc = await async_cmd(["podman", "version", "-f", "json"])
    if proc:
        assert proc.stdout is not None
        version_str = json.loads((await proc.stdout.read()).decode())["Client"][
            "Version"
        ]
        major, minor = version_str.split(".")[:2]
        if not (int(major) >= 3 and int(minor) >= 1):
            needs_fuse = True
            logger.warning("Podman version is too old for rootless native overlayfs")
    if needs_fuse:
        Config.native_overlayfs = False
        proc = await async_cmd(["command", "-v", "fuse-overlayfs"])
        if proc and proc.returncode:
            result = False
            logger.error(
                "Could not find fuse-overlayfs. Try: dnf install fuse-overlayfs"
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
