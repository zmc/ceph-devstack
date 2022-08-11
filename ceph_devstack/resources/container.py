import asyncio
import json
import os

from typing import Dict, List, Union

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
    watch_cmd: List[str] = ["podman", "container", "inspect", "{name}"]
    env_vars: Dict[str, Union[str, None]] = dict()

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

    async def apply(self, action: str):
        if action == "build":
            key = self.image
        else:
            key = self.name
        return await super().apply(action, key=key)

    async def build(self):
        if hasattr(self, "build_cmd"):
            await self.cmd(self.format_cmd(self.build_cmd), check=True)

    async def create(self):
        args = self.add_env_to_args(self.format_cmd(self.create_cmd))
        await self.cmd(args, check=True)

    async def start(self):
        await super().start()
        if "--health-cmd" in self.create_cmd or "--healthcheck-cmd" in self.create_cmd:
            rc = None
            while rc != 0:
                result = await self.cmd(
                    self.format_cmd(["podman", "healthcheck", "run", "{name}"]),
                    kwargs=dict(env=self.env_vars),
                )
                if result is None:
                    return
                rc = result.returncode
                await asyncio.sleep(1)

    async def exists(self, proc=None):
        proc = proc or await self.cmd(self.format_cmd(self.watch_cmd))
        if proc is None:
            return True
        await proc.wait()
        return proc.returncode == 0

    async def is_running(self):
        proc = await self.cmd(self.format_cmd(self.watch_cmd))
        if proc is None:
            return True
        if not await self.exists(proc):
            return False
        assert proc.stdout is not None
        result = json.loads((await proc.stdout.read()).decode())
        if not result:
            return False
        return result[0]["State"]["Status"].lower() == "running"
