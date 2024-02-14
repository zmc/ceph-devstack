from pathlib import Path
from packaging.version import parse as parse_version, Version

from ceph_devstack import logger
from ceph_devstack.host import host


async def check_requirements():
    result = True
    try:
        podman_info = await host.podman_info()
    except FileNotFoundError:
        logger.error("podman not found. Try: dnf install podman")
        return False
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
            f"Kernel version ({kernel_version}) is too old to support native rootless "
            f"overlayfs (needs {version_for_overlay})"
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
        proc = await host.arun(["command", "-v", "fuse-overlayfs"])
        if (await proc.wait()) >= 0:
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
            f"It must be set to 'crun' in {containers_conf_path}. "
            f"Afterward, run 'podman system reset'."
        )

    # SELinux
    if await host.selinux_enforcing():
        result = result and check_selinux_bool("container_manage_cgroup")
        result = result and check_selinux_bool("container_use_devices")

    # podman DNS plugin
    dns_plugin_path = "/usr/libexec/cni/dnsname"
    proc = await host.arun(["ls", dns_plugin_path])
    if (await proc.wait()) != 0:
        result = False
        logger.error(
            "Could not find the podman DNS plugin. Try: "
            "dnf install /usr/libexec/cni/dnsname"
        )

    # sysctl settings for OSD
    result = result and await check_sysctl_value("fs.aio-max-nr", 1048576)
    result = result and await check_sysctl_value("kernel.pid_max", 4194304)

    return result


async def check_selinux_bool(name):
    proc = await host.arun(["getsebool", name])
    assert proc.stdout is not None
    out = await proc.stdout.read()
    if out.decode().strip() != f"{name} --> on":
        logger.error(
            f"SELinux boolean '{name}' must be enabled. "
            f"Try: setsebool -P {name}=true"
        )
        return False
    return True


async def check_sysctl_value(name: str, min_value: int):
    proc = await host.arun(["sysctl", "-b", name])
    assert proc.stdout is not None
    out = await proc.stdout.read()
    current_value = int(out.decode().strip())
    if current_value < min_value:
        logger.error(
            f"sysctl setting {name} ({current_value}) is too low. Try: "
            f"sysctl {name}={min_value}"
        )
        return False
    return True
