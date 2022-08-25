import asyncio
import grp
import os
import tempfile

from collections import OrderedDict

from ceph_devstack import Config, logger
from ceph_devstack.resources.misc import Secret, Network
from ceph_devstack.resources.ceph.containers import (
    Postgres,
    Beanstalkd,
    Paddles,
    Pulpito,
    TestNode,
    Teuthology,
    Archive,
)
from ceph_devstack.util import get_local_hostname


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

    @property
    def containers(self):
        return OrderedDict(
            [
                (Postgres, 1),
                (Paddles, 1),
                (Beanstalkd, 1),
                (Pulpito, 1),
                (TestNode, Config.args.testnode_count),
                (Teuthology, 1),
                (Archive, 1),
            ]
        )

    async def check_requirements(self):
        result = True
        loop_control = "/dev/loop-control"
        if not os.path.exists(loop_control):
            result = False
            logger.error(f"{loop_control} does not exist!")
        elif not os.access(loop_control, os.W_OK):
            result = False
            stat = os.stat(loop_control)
            group_name = grp.getgrgid(stat.st_gid).gr_name
            logger.error(
                f"Cannot write to {loop_control}. "
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
        logger.info("Building images...")
        for kind in self.containers.keys():
            await kind().build()

    async def create(self):
        logger.info("Creating containers...")
        await CephDevStackNetwork().create()
        await SSHKeyPair().create()
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name).create())
        await asyncio.gather(*containers)

    async def start(self):
        logger.info("Starting containers...")
        for kind in self.containers:
            for name in self.container_names(kind):
                await kind(name=name).start()
        logger.info(
            "All containers are running. To monitor teuthology, try running: podman logs -f teuthology"
        )
        logger.info(f"View test results at http://{get_local_hostname()}:8081/")

    async def stop(self):
        logger.info("Stopping containers...")
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name).stop())
        await asyncio.gather(*containers)

    async def remove(self):
        logger.info("Removing containers...")
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name).remove())
        await asyncio.gather(*containers)
        await CephDevStackNetwork().remove()
        await SSHKeyPair().remove()

    async def watch(self):
        logger.info("Watching containers; will replace any that are stopped")
        containers = []
        for kind in self.containers:
            for name in self.container_names(kind):
                containers.append(kind(name=name))
        logger.info(f"Watching {containers}")
        while True:
            try:
                for container in containers:
                    if not await container.exists():
                        logger.info(
                            f"Container {container.name} was removed; replacing"
                        )
                        await container.create()
                        await container.start()
                    elif not await container.is_running():
                        logger.info(f"Container {container.name} stopped; restarting")
                        await container.start()
            except KeyboardInterrupt:
                break
