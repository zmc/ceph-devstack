from ceph_devstack import logger, PROJECT_ROOT
from ceph_devstack.requirements import Requirement, FixableRequirement


class HasSudo(Requirement):
    check_cmd = ["sudo", "true"]
    suggest_msg = "sudo access is required"


class LoopControlDeviceExists(FixableRequirement):
    device = "/dev/loop-control"
    check_cmd = ["test", "-e", device]
    suggest_msg = f"{device} does not exist"
    fix_cmd = ["sudo", "modprobe", "loop"]


class LoopControlDeviceWriteable(FixableRequirement):
    device = "/dev/loop-control"
    check_cmd = ["test", "-w", device]
    suggest_msg = f"Cannot write to {device}"

    async def check(self):
        if not (result := await super().check()):
            group = (
                self.host.run(["stat", "--printf", "%G", self.device])
                .communicate()[0]
                .decode()
            )
            user = self.host.run(["whoami"]).communicate()[0].strip().decode()
            if self.host.type == "local":
                self.fix_cmd = ["sudo", "usermod", "-a", "-G", group, user]
            else:
                self.fix_cmd = ["sudo", "chgrp", user, self.device]
            self.suggest_msg = f"Cannot write to {self.device}"
        return result

    async def suggest(self):
        await super().suggest()
        if self.host.type == "local":
            logger.warning(
                "Note that group modifications require a logout to take effect."
            )


class SELinuxModule(FixableRequirement):
    def __init__(self):
        fix_cmd = self.fix_cmd_prebuilt
        if self.host.type == "remote":
            fix_cmd = ["podman", "machine", "ssh", "--"] + fix_cmd
        self.fix_cmd = fix_cmd

    fix_cmd_build = [
        "(sudo",
        "dnf",
        "install",
        "policycoreutils-devel",
        "selinux-policy-devel",
        "&&",
        "cd",
        str(PROJECT_ROOT),
        "&&",
        "make",
        "-f",
        "/usr/share/selinux/devel/Makefile",
        "ceph_devstack.pp",
        "&&",
        "sudo",
        "semodule",
        "-i",
        "ceph_devstack.pp)",
    ]
    fix_cmd_prebuilt = [
        "sudo",
        "semodule",
        "-i",
        str(PROJECT_ROOT / "ceph_devstack.pp"),
    ]
    suggest_msg = (
        "SELinux is in Enforcing mode. To run nested rootless podman "
        "containers, it is necessary to install ceph-devstack's SELinux "
        "module"
    )

    async def check(self):
        proc = await self.host.arun(["sudo", "semodule", "-l"])
        assert proc.stdout is not None
        await proc.wait()
        out = (await proc.stdout.read()).decode()
        return "ceph_devstack" in out.split("\n")
