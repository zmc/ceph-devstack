import asyncio
import grp
import logging
import os
import tempfile

from collections import OrderedDict

from ceph_devstack import Config
from ceph_devstack.resources.misc import Secret, Network
from ceph_devstack.resources.ceph.containers import (
    Postgres,
    Beanstalkd,
    Paddles,
    Pulpito,
    TestNode,
    Teuthology,
)
from ceph_devstack.util import async_cmd

logger = logging.getLogger()


class SSHKeyPair(Secret):
    _name = "id_rsa"
    cmd_vars = ["name", "privkey_path", "pubkey_path"]
    privkey_path = "id_rsa"
    pubkey_path = "id_rsa.pub"
    create_cmds = [
        ["podman", "secret", "create", "{name}", "{privkey_path}"],
        ["podman", "secret", "create", "{name}.pub", "{pubkey_path}"],
    ]
    remove_cmds = [
        ["podman", "secret", "rm", "{name}"],
        ["podman", "secret", "rm", "{name}.pub"],
    ]

    async def create(self):
        await self._get_ssh_keys()
        for create_cmd in self.create_cmds:
            await self.cmd(self.format_cmd(create_cmd), check=True)

    async def remove(self):
        for remove_cmd in self.remove_cmds:
            await self.cmd(self.format_cmd(remove_cmd))

    async def _get_ssh_keys(self):
        if Config.args.dry_run:
            return
        privkey_path = os.environ.get("SSH_PRIVKEY_PATH")
        self.pubkey_path = "/dev/null"
        if not privkey_path:
            privkey_path = tempfile.mktemp(
                prefix="teuthology-ssh-key-",
                dir="/tmp",
            )
            await self.cmd(
                ["ssh-keygen", "-t", "rsa", "-N", "", "-f", privkey_path], check=True
            )
            self.pubkey_path = f"{privkey_path}.pub"
        self.privkey_path = privkey_path


class CephDevStackNetwork(Network):
    _name = "ceph-devstack"


class CephDevStack:
    networks = [CephDevStackNetwork]
    secrets = [SSHKeyPair]
    containers = OrderedDict(
        [
            (Postgres, 1),
            (Paddles, 1),
            (Beanstalkd, 1),
            (Pulpito, 1),
            (TestNode, 3),
            (Teuthology, 1),
        ]
    )

    async def check_requirements(self):
        result = True
        proc = await async_cmd(["sudo", "-v"])
        if proc and proc.returncode:
            result = False
            logger.error("sudo access is required")
        proc = await async_cmd(["command", "-v", "fuse-overlayfs"])
        if proc and proc.returncode:
            result = False
            logger.error(
                "Could not find fuse-overlayfs. Try: dnf install fuse-overlayfs"
            )
        if not os.access("/dev/loop-control", os.W_OK):
            result = False
            stat = os.stat("/dev/loop-control")
            group_name = grp.getgrgid(stat.st_gid).gr_name
            logger.error(
                "Cannot write to /dev/loop-control. "
                f"Try: sudo usermod -a -G {group_name} {os.getlogin()}"
            )
        return result

    async def apply(self, action):
        if not await self.check_requirements():
            raise RuntimeError("Requirements not met!")
        return await getattr(self, action)()

    def container_names(self, kind):
        count = self.containers[kind]
        name = kind.__name__.lower()
        if count > 1:
            return [f"{name}_{i}" for i in range(count)]
        return [""]

    async def build(self):
        for kind in self.containers.keys():
            await kind().build()

    async def create(self):
        await CephDevStackNetwork().create()
        await SSHKeyPair().create()
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name).create())
        await asyncio.gather(*containers)

    async def start(self):
        for kind in self.containers:
            for name in self.container_names(kind):
                await kind(name=name).start()

    async def stop(self):
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name).stop())
        await asyncio.gather(*containers)

    async def remove(self):
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name).remove())
        await asyncio.gather(*containers)
        await CephDevStackNetwork().remove()
        await SSHKeyPair().remove()

    async def watch(self):
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name))
        logger.info(f"Watching {containers}")
        while True:
            try:
                for container in containers:
                    if not await container.is_running():
                        logger.info(f"Container {container.name} stopped!")
                        await container.create()
                        await container.start()
                        await asyncio.sleep(60)
                await asyncio.sleep(10)
            except KeyboardInterrupt:
                break