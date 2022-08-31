import asyncio
import json
import os

from typing import Dict, List, Optional

from ceph_devstack import Config, logger
from ceph_devstack.resources import PodmanResource


class Container(PodmanResource):
    image: str
    network: str
    secret: List[str]
    cmd_vars: List[str] = ["name", "image"]
    build_cmd: List[str]
    create_cmd: List[str] = ["podman", "container", "create", "{name}"]
    remove_cmd: List[str] = ["podman", "container", "rm", "-f", "{name}"]
    start_cmd: List[str] = ["podman", "container", "start", "{name}"]
    stop_cmd: List[str] = ["podman", "container", "stop", "{name}"]
    exists_cmd: List[str] = ["podman", "container", "inspect", "{name}"]
    env_vars: Dict[str, Optional[str]] = {}

    def __init__(self, name: str = ""):
        super().__init__(name)
        self.env_vars = {**self.__class__.env_vars}
        for key in self.env_vars:
            if key in os.environ:
                self.env_vars[key] = os.environ[key]

    def add_env_to_args(self, args: List):
        args = super().format_cmd(args)
        for key, value in self.env_vars.items():
            args.insert(-1, "-e")
            args.insert(-1, f"{key}={value}")
        return args

    async def build(self):
        if not getattr(self, "build_cmd", None):
            return
        logger.debug(f"{self.name}: building")
        await self.cmd(self.format_cmd(self.build_cmd), check=True)
        logger.debug(f"{self.name}: built")

    async def create(self):
        if not getattr(self, "create_cmd", None):
            return
        if await self.exists():
            return
        args = self.add_env_to_args(self.format_cmd(self.create_cmd))
        logger.debug(f"{self.name}: creating")
        kwargs = {}
        if not Config.native_overlayfs:
            kwargs["env"] = {
                "CONTAINERS_STORAGE_CONF": os.path.normpath(
                    os.path.join(
                        os.path.dirname(os.path.abspath(__file__)),
                        "../podman_config/storage.conf",
                    )
                )
            }
        await self.cmd(args, kwargs, check=True)
        logger.debug(f"{self.name}: created")

    async def start(self):
        if not getattr(self, "start_cmd", None):
            return
        logger.debug(f"{self.name}: starting")
        await self.cmd(self.format_cmd(self.start_cmd), check=True)
        if "--health-cmd" in self.create_cmd or "--healthcheck-cmd" in self.create_cmd:
            rc = None
            while rc != 0:
                result = await self.cmd(
                    self.format_cmd(["podman", "healthcheck", "run", "{name}"]),
                    kwargs={"env": self.env_vars},
                )
                if result is None:
                    break
                rc = result.returncode
                await asyncio.sleep(1)
        logger.debug(f"{self.name}: started")

    async def stop(self):
        if not getattr(self, "stop_cmd", None):
            return
        logger.debug(f"{self.name}: stopping")
        await self.cmd(self.format_cmd(self.stop_cmd))
        logger.debug(f"{self.name}: stopping")

    async def remove(self):
        if not getattr(self, "remove_cmd", None):
            return
        logger.debug(f"{self.name}: removing")
        await super().remove()
        logger.debug(f"{self.name}: removed")

    async def is_running(self):
        proc = await self.cmd(self.format_cmd(self.exists_cmd))
        if proc is None:
            return True
        if not await self.exists(proc):
            return False
        assert proc.stdout is not None
        result = json.loads((await proc.stdout.read()).decode())
        if not result:
            return False
        return result[0]["State"]["Status"].lower() == "running"
