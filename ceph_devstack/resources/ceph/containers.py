import os
import sys

from pathlib import Path
from typing import List

from ceph_devstack import config, DEFAULT_CONFIG_PATH
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

    def __init__(self, name: str = ""):
        super().__init__(name)
        username = self.env_vars["APP_DB_USER"]
        password = self.env_vars["APP_DB_PASS"]
        db_name = self.env_vars["APP_DB_NAME"]
        self.paddles_sqla_url = (
            f"postgresql+psycopg2://{username}:{password}@postgres:5432/{db_name}"
        )


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
    cmd_vars: List[str] = ["name", "image"]
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
        "AUDIT_CONTROL",
    ]
    env_vars = {
        "SSH_PUBKEY": "",
        "CEPH_VOLUME_ALLOW_LOOP_DEVICES": "true",
    }

    def __init__(self, name: str = ""):
        super().__init__(name=name)
        self.index = 0
        if "_" in self.name:
            self.index = int(self.name.split("_")[-1])
        self.osd_count = config["containers"]["testnode"].get("osd_count", 1)
        self.devices = [self.device_name(i) for i in range(self.osd_count)]

    @property
    def loop_img_dir(self):
        return (Path(config["data_dir"]) / "disk_images").expanduser()

    @property
    def create_cmd(self):
        return [
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
            ",".join(self.capabilities),
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
            # The below was bizarrely causing this error message:
            # No such file or directory: OCI runtime attempted to invoke a command that was
            # not found
            # That was causing the container to fail to start up.
            "-v",
            "/dev/null:/sys/class/dmi/id/board_serial",
            "-v",
            "/dev/null:/sys/class/dmi/id/chassis_serial",
            "-v",
            "/dev/null:/sys/class/dmi/id/product_serial",
            *self.additional_volumes,
            "--device",
            "/dev/net/tun",
            *[f"--device={device}" for device in self.devices],
            "--name",
            "{name}",
            "{image}",
        ]

    @property
    def additional_volumes(self):
        volumes = []
        if DEFAULT_CONFIG_PATH.parent.joinpath("sshd_config").exists():
            volumes.extend(
                [
                    "-v",
                    f"{DEFAULT_CONFIG_PATH.parent.joinpath('sshd_config')}:/etc/ssh/sshd_config.d/teuthology.conf:z",
                ]
            )
        return volumes

    async def create(self):
        if not await self.exists():
            await self.create_loop_devices()
        await super().create()

    async def remove(self):
        await super().remove()
        await self.remove_loop_devices()

    async def create_loop_devices(self):
        for device in self.devices:
            await self.create_loop_device(device)

    async def remove_loop_devices(self):
        for device in self.devices:
            await self.remove_loop_device(device)

    async def create_loop_device(self, device: str):
        size = config["containers"]["testnode"]["loop_device_size"]
        os.makedirs(self.loop_img_dir, exist_ok=True)
        proc = await self.cmd(["lsmod", "|", "grep", "loop"])
        if proc and await proc.wait() != 0:
            await self.cmd(["sudo", "modprobe", "loop"])
        loop_img_name = os.path.join(self.loop_img_dir, self.device_image(device))
        await self.remove_loop_device(device)
        device_pos = device.lstrip("/dev/loop")
        await self.cmd(
            [
                "sudo",
                "mknod",
                "-m700",
                device,
                "b",
                "7",
                device_pos,
            ],
            check=True,
        )
        await self.cmd(
            ["sudo", "chown", f"{os.getuid()}:{os.getgid()}", device],
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
                f"seek={size}",
            ],
            check=True,
        )
        await self.cmd(["sudo", "losetup", device, loop_img_name], check=True)

    async def remove_loop_device(self, device: str):
        loop_img_name = os.path.join(self.loop_img_dir, self.device_image(device))
        if os.path.ismount(device):
            await self.cmd(["umount", device], check=True)
        if host.path_exists(device):
            await self.cmd(["sudo", "losetup", "-d", device])
            await self.cmd(["sudo", "rm", "-f", device], check=True)
        if host.path_exists(loop_img_name):
            os.remove(loop_img_name)

    def device_name(self, index: int):
        return f"/dev/loop{self.osd_count * self.index + index}"

    def device_image(self, device: str):
        return f"{self.name}-{device.lstrip('/dev/loop')}"


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
        ssh_auth_socket = os.environ.get("SSH_AUTH_SOCK")
        if ssh_auth_socket:
            cmd += [
                "-v",
                f"{ssh_auth_socket}:{ssh_auth_socket}",
                "-e",
                f"SSH_AUTH_SOCK={ssh_auth_socket}",
            ]
        custom_conf = os.environ.get("TEUTHOLOGY_CONF")
        if custom_conf:
            cmd += [
                "-v",
                f"{custom_conf}:/tmp/conf.yaml",
                "-e",
                "TEUTHOLOGY_CONF=/tmp/conf.yaml",
            ]
        teuthology_yaml = os.environ.get("TEUTHOLOGY_YAML")
        if teuthology_yaml:
            cmd += [
                "-v",
                f"{teuthology_yaml}:/root/.teuthology.yaml",
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
        "TEUTHOLOGY_SUITE_EXTRA_ARGS": "",
    }

    @property
    def archive_dir(self):
        return Path(config["data_dir"]) / "archive"

    async def create(self):
        self.archive_dir.expanduser().resolve().mkdir(parents=True, exist_ok=True)
        await super().create()
