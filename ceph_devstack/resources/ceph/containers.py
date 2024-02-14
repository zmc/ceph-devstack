import os
import sys

from pathlib import Path
from typing import List

from ceph_devstack import config
from ceph_devstack.host import host
from ceph_devstack.resources.container import Container


ARCHIVE_MOUNT_SUFFIX = "" if sys.platform == "darwin" else ":z"


class Postgres(Container):
    create_cmd = [
        "podman",
        "container",
        "create",
        "-i",
        "--network",
        "ceph-devstack",
        "-p",
        "5432:5432",
        "--health-cmd",
        "CMD pg_isready -q -d paddles -U admin",
        "--health-interval",
        "10s",
        "--health-retries",
        "2",
        "--health-timeout",
        "5s",
        "--name",
        "{name}",
        "{image}",
    ]
    env_vars = {
        "POSTGRES_USER": "root",
        "POSTGRES_PASSWORD": "password",
        "APP_DB_USER": "admin",
        "APP_DB_PASS": "password",
        "APP_DB_NAME": "paddles",
    }


class Beanstalk(Container):
    _name = "beanstalk"
    create_cmd = [
        "podman",
        "container",
        "create",
        "-i",
        "--network",
        "ceph-devstack",
        "-p",
        "11300:11300",
        "--name",
        "{name}",
        "{image}",
    ]


class Paddles(Container):
    create_cmd = [
        "podman",
        "container",
        "create",
        "-i",
        "--network",
        "ceph-devstack",
        "-p",
        "8080:8080",
        "--health-cmd",
        "CMD curl -f http://0.0.0.0:8080",
        "--health-interval",
        "10s",
        "--health-retries",
        "30",
        "--health-timeout",
        "5s",
        "--name",
        "{name}",
        "{image}",
    ]
    env_vars = {
        "PADDLES_SERVER_HOST": "0.0.0.0",
        "PADDLES_SQLALCHEMY_URL": "postgresql+psycopg2://admin:password@postgres:5432/paddles",
        "PADDLES_JOB_LOG_HREF_TEMPL": f"http://{host.hostname()}:8000"
        "/{run_name}/{job_id}/teuthology.log",
    }


class Archive(Container):
    cmd_vars: List[str] = ["name", "image", "archive_dir"]
    create_cmd = [
        "podman",
        "container",
        "create",
        "-i",
        "--network",
        "ceph-devstack",
        "-p",
        "8000:8000",
        "-v",
        "{archive_dir}:/archive" + ARCHIVE_MOUNT_SUFFIX,
        "--name",
        "{name}",
        "{image}",
        "python3",
        "-m",
        "http.server",
        "-d",
        "/archive",
    ]

    @property
    def archive_dir(self):
        return Path(config["data_dir"]) / "archive"


class Pulpito(Container):
    create_cmd = [
        "podman",
        "container",
        "create",
        "-i",
        "--network",
        "ceph-devstack",
        "-p",
        "8081:8081",
        "--health-cmd",
        "CMD curl -f http://0.0.0.0:8081",
        "--health-interval",
        "10s",
        "--health-retries",
        "10",
        "--health-timeout",
        "5s",
        "--name",
        "{name}",
        "{image}",
    ]
    env_vars = {
        "PULPITO_PADDLES_ADDRESS": "http://paddles:8080",
    }


class TestNode(Container):
    cmd_vars: List[str] = ["name", "image", "loop_dev_name"]
    capabilities = [
        "SYS_ADMIN",
        "NET_ADMIN",
        "SYS_TIME",
        "SYS_RAWIO",
        "MKNOD",
        "NET_RAW",
        "SETUID",
        "SETGID",
        "CHOWN",
        "SYS_PTRACE",
        "SYS_TTY_CONFIG",
        "AUDIT_WRITE",
    ]
    create_cmd = [
        "podman",
        "container",
        "create",
        "--rm",
        "-i",
        "--network",
        "ceph-devstack",
        "--systemd=always",
        "--cgroupns=host",
        "--secret",
        "id_rsa.pub",
        "-p",
        "22",
        "--cap-add",
        ",".join(capabilities),
        "--security-opt",
        "unmask=/sys/dev/block",
        "-v",
        "/sys/dev/block:/sys/dev/block",
        "-v",
        "/sys/fs/cgroup:/sys/fs/cgroup",
        "-v",
        "/dev/fuse:/dev/fuse",
        "-v",
        "/dev/disk:/dev/disk",
        # cephadm tries to access these DMI-related files, and by default they
        # have 600 permissions on the host. It appears to be ok if they are
        # empty, though.
        "-v",
        "/dev/null:/sys/class/dmi/id/board_serial",
        "-v",
        "/dev/null:/sys/class/dmi/id/chassis_serial",
        "-v",
        "/dev/null:/sys/class/dmi/id/product_serial",
        "--device",
        "/dev/net/tun",
        "--device",
        "{loop_dev_name}",
        "--name",
        "{name}",
        "{image}",
    ]
    env_vars = {
        "SSH_PUBKEY": "",
        "CEPH_VOLUME_ALLOW_LOOP_DEVICES": "true",
    }

    def __init__(self, name: str = ""):
        super().__init__(name=name)
        self.loop_index = 0
        self.loop_img_name = self.name
        if "_" in self.name:
            self.loop_index = int(self.name.split("_")[-1])
        else:
            self.loop_img_name += str(self.loop_index)
        self.loop_dev_name = f"/dev/loop{self.loop_index}"

    @property
    def loop_img_dir(self):
        return (Path(config["data_dir"]) / "disk_images").expanduser()

    async def create(self):
        if not await self.exists():
            await self.create_loop_device()
        await super().create()

    async def remove(self):
        await super().remove()
        await self.remove_loop_device()

    async def create_loop_device(self):
        size_gb = 5
        os.makedirs(self.loop_img_dir, exist_ok=True)
        proc = await self.cmd(["lsmod", "|", "grep", "loop"])
        if proc and await proc.wait() != 0:
            await self.cmd(["sudo", "modprobe", "loop"])
        loop_img_name = os.path.join(self.loop_img_dir, self.loop_img_name)
        await self.remove_loop_device()
        await self.cmd(
            [
                "sudo",
                "mknod",
                "-m700",
                self.loop_dev_name,
                "b",
                "7",
                str(self.loop_index),
            ],
            check=True,
        )
        await self.cmd(
            ["sudo", "chown", f"{os.getuid()}:{os.getgid()}", self.loop_dev_name],
            check=True,
        )
        await self.cmd(
            [
                "sudo",
                "dd",
                "if=/dev/null",
                f"of={loop_img_name}",
                "bs=1",
                "count=0",
                f"seek={size_gb}G",
            ],
            check=True,
        )
        await self.cmd(
            ["sudo", "losetup", self.loop_dev_name, loop_img_name], check=True
        )

    async def remove_loop_device(self):
        loop_img_name = os.path.join(self.loop_img_dir, self.loop_img_name)
        if os.path.ismount(self.loop_dev_name):
            await self.cmd(["umount", self.loop_dev_name], check=True)
        if host.path_exists(self.loop_dev_name):
            await self.cmd(["sudo", "losetup", "-d", self.loop_dev_name])
            await self.cmd(["sudo", "rm", "-f", self.loop_dev_name], check=True)
        if host.path_exists(loop_img_name):
            os.remove(loop_img_name)


class Teuthology(Container):
    cmd_vars: List[str] = ["name", "image", "image_tag", "archive_dir"]

    build_cmd: List[str] = [
        "podman",
        "build",
        "-t",
        "{name}:{image_tag}",
        "-f",
        "./containers/teuthology-dev/Dockerfile",
        ".",
    ]

    @property
    def create_cmd(self):
        cmd = [
            "podman",
            "container",
            "create",
            "-i",
            "--label",
            f"testnode_count={config['containers']['testnode']['count']}",
            "--network",
            "ceph-devstack",
            "--secret",
            "id_rsa",
            "-v",
            "{archive_dir}:/archive_dir" + ARCHIVE_MOUNT_SUFFIX,
        ]
        ansible_inv = os.environ.get("ANSIBLE_INVENTORY_PATH")
        if ansible_inv:
            cmd += [
                "-v",
                f"{ansible_inv}/inventory:/etc/ansible/hosts",
                "-v",
                f"{ansible_inv}/secrets:/etc/ansible/secrets",
            ]
        cmd += [
            "--name",
            "{name}",
            "{image}",
        ]
        return cmd

    env_vars = {
        "SSH_PRIVKEY": "",
        "SSH_PRIVKEY_FILE": "",
        "TEUTHOLOGY_MACHINE_TYPE": "",
        "TEUTHOLOGY_TESTNODES": "",
        "TEUTHOLOGY_BRANCH": "",
        "TEUTHOLOGY_CEPH_BRANCH": "",
        "TEUTHOLOGY_CEPH_REPO": "",
        "TEUTHOLOGY_SUITE": "",
        "TEUTHOLOGY_SUITE_BRANCH": "",
        "TEUTHOLOGY_SUITE_REPO": "",
    }

    @property
    def archive_dir(self):
        return Path(config["data_dir"]) / "archive"

    async def create(self):
        self.archive_dir.expanduser().resolve().mkdir(parents=True, exist_ok=True)
        await super().create()
