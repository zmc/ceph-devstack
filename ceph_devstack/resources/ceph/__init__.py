import asyncio
import contextlib
import os
import tempfile

from collections import OrderedDict
from subprocess import CalledProcessError

from ceph_devstack import config, logger
from ceph_devstack.host import host
from ceph_devstack.resources.misc import Secret, Network
from ceph_devstack.resources.ceph.containers import (
    Postgres,
    Beanstalk,
    Paddles,
    Pulpito,
    TestNode,
    Teuthology,
    Archive,
)
from ceph_devstack.resources.ceph.requirements import (
    HasSudo,
    LoopControlDeviceExists,
    LoopControlDeviceWriteable,
    SELinuxModule,
)


class SSHKeyPair(Secret):
    _name = "id_rsa"
    cmd_vars = ["name", "privkey_path", "pubkey_path"]
    privkey_path = "id_rsa"
    pubkey_path = "id_rsa.pub"
    exists_cmds = [
        ["podman", "secret", "inspect", "{name}"],
        ["podman", "secret", "inspect", "{name}.pub"],
    ]
    create_cmds = [
        ["podman", "secret", "create", "{name}", "{privkey_path}"],
        ["podman", "secret", "create", "{name}.pub", "{pubkey_path}"],
    ]
    remove_cmds = [
        ["podman", "secret", "rm", "{name}"],
        ["podman", "secret", "rm", "{name}.pub"],
    ]

    async def exists(self):
        for exists_cmd in self.exists_cmds:
            proc = await self.cmd(self.format_cmd(exists_cmd), check=False)
            if await proc.wait():
                return False
        return True

    async def create(self):
        if await self.exists():
            return
        await self._get_ssh_keys()
        for create_cmd in self.create_cmds:
            await self.cmd(self.format_cmd(create_cmd), check=True)

    async def remove(self):
        for remove_cmd in self.remove_cmds:
            await self.cmd(self.format_cmd(remove_cmd))

    async def _get_ssh_keys(self):
        privkey_path = os.environ.get("SSH_PRIVKEY_PATH")
        self.pubkey_path = "/dev/null"
        if not privkey_path:
            privkey_path = tempfile.mktemp(
                prefix="teuthology-ssh-key-",
                dir="/tmp",
            )
            await self.cmd(
                ["ssh-keygen", "-t", "rsa", "-N", "", "-f", privkey_path],
                check=True,
                force_local=True,
            )
            self.pubkey_path = f"{privkey_path}.pub"
        self.privkey_path = privkey_path


class CephDevStackNetwork(Network):
    _name = "ceph-devstack"


class CephDevStack:
    networks = [CephDevStackNetwork]
    secrets = [SSHKeyPair]

    async def get_containers(self):
        return OrderedDict(
            [
                (Postgres, 1),
                (Paddles, 1),
                (Beanstalk, 1),
                (Pulpito, 1),
                (Teuthology, 1),
                (TestNode, await self.get_testnode_count()),
                (Archive, 1),
            ]
        )

    async def get_testnode_count(self) -> int:
        teuth = Teuthology()
        try:
            data = await teuth.inspect()
            return int(data[0]["config"]["Labels"]["testnode_count"])
        except (KeyError, IndexError, CalledProcessError):
            return config["containers"]["testnode"]["count"]

    async def check_requirements(self):
        result = True

        result = has_sudo = await HasSudo().evaluate()
        result = result and await LoopControlDeviceExists().evaluate()
        result = result and await LoopControlDeviceWriteable().evaluate()

        # Check for SELinux being enabled and Enforcing; then check for the
        # presence of our module. If necessary, inform the user and instruct
        # them how to build and install.
        if has_sudo and await host.selinux_enforcing():
            result = result and await SELinuxModule().evaluate()

        for name, obj in config["containers"].items():
            if (repo := obj.get("repo")) and not host.path_exists(repo):
                result = False
                logger.error(f"Repo for {name} not found at {repo}")
        return result

    async def apply(self, action):
        return await getattr(self, action)()

    async def get_container_names(self, kind):
        count = (await self.get_containers())[kind]
        name = kind.__name__.lower()
        if count > 1:
            return [f"{name}_{i}" for i in range(count)]
        return [""]

    async def pull(self):
        logger.info("Pulling images...")
        images = config["args"]["image"]
        for kind in (await self.get_containers()).keys():
            if images and str(kind.__name__).lower() not in images:
                continue
            await kind().pull()

    async def build(self):
        logger.info("Building images...")
        images = config["args"]["image"]
        for kind in (await self.get_containers()).keys():
            if images and str(kind.__name__).lower() not in images:
                continue
            await kind().build()

    async def create(self):
        logger.info("Creating containers...")
        await CephDevStackNetwork().create()
        await SSHKeyPair().create()
        containers = []
        for kind in (await self.get_containers()).keys():
            for name in await self.get_container_names(kind):
                containers.append(kind(name=name).create())
        await asyncio.gather(*containers)

    async def start(self):
        await self.create()
        logger.info("Starting containers...")
        for kind in (await self.get_containers()).keys():
            for name in await self.get_container_names(kind):
                await kind(name=name).start()
        logger.info(
            "All containers are running. To monitor teuthology, try running: podman "
            "logs -f teuthology"
        )
        hostname = host.hostname()
        logger.info(f"View test results at http://{hostname}:8081/")

    async def stop(self):
        logger.info("Stopping containers...")
        containers = []
        for kind in (await self.get_containers()).keys():
            for name in await self.get_container_names(kind):
                containers.append(kind(name=name).stop())
        await asyncio.gather(*containers)

    async def remove(self):
        logger.info("Removing containers...")
        containers = []
        for kind in (await self.get_containers()).keys():
            for name in await self.get_container_names(kind):
                containers.append(kind(name=name).remove())
        await asyncio.gather(*containers)
        await CephDevStackNetwork().remove()
        await SSHKeyPair().remove()

    async def watch(self):
        logger.info("Watching containers; will replace any that are stopped")
        containers = []
        for kind, count in (await self.get_containers()).items():
            if not count > 0:
                continue
            for name in await self.get_container_names(kind):
                containers.append(kind(name=name))
        logger.info(f"Watching {containers}")
        while True:
            try:
                for container in containers:
                    with contextlib.suppress(CalledProcessError):
                        if not await container.exists():
                            logger.info(
                                f"Container {container.name} was removed; replacing"
                            )
                            await container.create()
                            await container.start()
                        elif not await container.is_running():
                            logger.info(
                                f"Container {container.name} stopped; restarting"
                            )
                            await container.start()
            except KeyboardInterrupt:
                break
