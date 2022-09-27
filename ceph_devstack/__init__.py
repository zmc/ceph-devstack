import argparse
import logging
import os
import yaml

from pathlib import Path, PosixPath
from typing import List


logging.basicConfig(
    format="%(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ceph-devstack")


def represent_path(dumper: yaml.dumper.SafeDumper, data: PosixPath) -> yaml.Node:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.SafeDumper.add_representer(
    PosixPath,
    represent_path,
)


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Instead of running commands, print them",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Be more verbose",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("~/.local/share/ceph-devstack"),
        help="Store temporary data e.g. disk images here",
    )
    parser.add_argument(
        "--config-file",
        type=Path,
        default=Path("~/.config/ceph-devstack/config.yml"),
        help="Path to the ceph-devstack config file",
    )
    parser.add_argument(
        "--ceph-repo",
        type=Path,
        default=Path("~/src/ceph"),
        help="Path to ceph repository",
    )
    parser.add_argument(
        "--teuthology-repo",
        type=Path,
        default=Path("~/src/teuthology"),
        help="Path to teuthology repository",
    )
    parser.add_argument(
        "--testnode-count",
        type=int,
        default=3,
        help="How many testnode containers to create",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("doctor", help="Check that the system meets requirements")
    parser_build = subparsers.add_parser("build", help="Build container images")
    parser_build.add_argument(
        "image",
        nargs="*",
        help="Specific image(s) to build",
    )
    parser_create = subparsers.add_parser(
        "create",
        help="Create the cluster",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_create.add_argument(
        "-b",
        "--build",
        action="store_true",
        default=False,
        help="Build images before creating",
    )
    parser_create.add_argument(
        "-w",
        "--wait",
        action="store_true",
        default=False,
        help="Leave the cluster running - and don't auto-schedule anything",
    )
    subparsers.add_parser("remove", help="Destroy the cluster")
    subparsers.add_parser("start", help="Start the cluster")
    subparsers.add_parser("stop", help="Stop the cluster")
    subparsers.add_parser(
        "watch", help="Monitor the cluster, recreating containers as necessary"
    )
    parsed_args = parser.parse_args(args)
    return parsed_args


class Config:
    args = parse_args([])
    storeable_args = ["teuthology_repo", "ceph_repo", "data_dir"]
    native_overlayfs: bool = True

    @classmethod
    @property
    def config_file(cls) -> Path:
        return Path(cls.args.config_file).expanduser()

    @classmethod
    @property
    def data_dir(cls) -> Path:
        return Path(cls.args.data_dir).expanduser()

    @classmethod
    @property
    def teuthology_repo(cls) -> Path:
        return Path(cls.args.teuthology_repo).expanduser()

    @classmethod
    @property
    def ceph_repo(cls) -> Path:
        return Path(cls.args.ceph_repo).expanduser()

    @classmethod
    def save(cls):
        os.makedirs(cls.config_file.parent, exist_ok=True)
        conf_obj = {key: getattr(cls.args, key) for key in cls.storeable_args}
        cls.config_file.write_text(yaml.safe_dump(conf_obj))

    @classmethod
    def load(cls):
        if cls.config_file.exists():
            obj = yaml.safe_load(cls.config_file.read_text())
            for k, v in obj.items():
                if getattr(cls.args, k) != v:
                    logger.debug(f"Using value from config: {k}={v}")
                    setattr(cls.args, k, v)
        return cls.args
