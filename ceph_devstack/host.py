import logging
import os
import pathlib
import socket
import sys
import yaml

from packaging.version import parse as parse_version, Version
from typing import Dict, List, Optional, Union

from .exec import Command

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Host:
    type = "local"

    def cmd(
        self,
        args: List[str],
        cwd: Optional[pathlib.Path] = None,
        env: Optional[Dict] = None,
    ) -> Command:
        return Command(args, cwd=cwd, env=env)

    def run(
        self,
        args: List[str],
        cwd: Optional[pathlib.Path] = None,
        env: Optional[Dict] = None,
    ):
        return self.cmd(args, cwd=cwd, env=env).run()

    async def arun(
        self,
        args: List[str],
        cwd: Optional[pathlib.Path] = None,
        env: Optional[Dict] = None,
    ):
        return await self.cmd(args, cwd=cwd, env=env).arun()

    def path_exists(self, path: Union[str, pathlib.Path]):
        if isinstance(path, pathlib.Path):
            return path.exists()
        return os.path.exists(path)

    def hostname(self) -> str:
        name = socket.getfqdn()
        try:
            socket.gethostbyname(name)
            return name
        except socket.gaierror:
            return "localhost"

    def kernel_version(self) -> Version:
        if not hasattr(self, "_kernel_version"):
            proc = self.run(["uname", "-r"])
            assert proc.stdout is not None
            assert proc.wait() == 0, "`uname -r` failed?!"
            raw_version = proc.stdout.read().decode().strip()
            self._kernel_version = parse_version(raw_version.split("-")[0])
        return self._kernel_version

    async def podman_info(self, force: bool = False) -> Dict:
        if force or not hasattr(self, "_podman_info"):
            proc = await self.arun(["podman", "info"])
            assert proc.stdout is not None
            await proc.wait()
            stdout = await proc.stdout.read()
            self._podman_info = yaml.safe_load(stdout.decode().strip())
        return self._podman_info

    async def selinux_enforcing(self) -> bool:
        proc = await host.arun(["cat", "/sys/fs/selinux/enforce"])
        assert proc.stdout is not None
        await proc.wait()
        out = (await proc.stdout.read()).decode()
        return proc.returncode == 0 and out == "1"

    async def check_selinux_bool(self, name: str):
        proc = await host.arun(["getsebool", name])
        assert proc.stdout is not None
        out = await proc.stdout.read()
        if out.decode().strip() != f"{name} --> on":
            return False
        return True

    async def get_sysctl_value(self, name: str) -> int:
        proc = await host.arun(["sysctl", "-b", name])
        assert proc.stdout is not None
        out = await proc.stdout.read()
        return int(out.decode().strip())


class LocalHost(Host):
    pass


class RemoteHost(Host):
    type = "remote"
    base_args = ["podman", "machine", "ssh", "--"]

    def cmd(
        self,
        args: List[str],
        cwd: Optional[pathlib.Path] = None,
        env: Optional[Dict] = None,
    ):
        if args[0] != "podman":
            args = self.base_args + args
        return super().cmd(args, cwd=cwd, env=env)

    def path_exists(self, path: Union[str, pathlib.Path]):
        path = os.path.expanduser(path)
        proc = host.run(["ls", path])
        return proc.returncode == 0

    def hostname(self) -> str:
        proc = self.run(["hostname"])
        assert proc.stdout is not None
        return proc.stdout.read().decode().strip()


local_host = LocalHost()

if sys.platform == "darwin":
    host = RemoteHost()
else:
    host = local_host
