import argparse
import logging
import os
import pathlib
import yaml

from typing import List


logging.basicConfig(
    format="%(levelname)s:%(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ceph-devstack")


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
        type=pathlib.Path,
        default="~/.local/share/ceph-devstack",
        help="Store temporary data e.g. disk images here",
    )
    parser.add_argument(
        "--config-file",
        type=pathlib.Path,
        default="~/.config/ceph-devstack/config.yml",
        help="Path to the ceph-devstack config file",
    )
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("build", help="Build containers")
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
    parser.add_argument(
        "--testnode-count",
        type=int,
        default=3,
        help="How many testnode containers to create",
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
    native_overlayfs: bool = True

    @classmethod
    @property
    def config_file(cls):
        return cls.args.config_file.expanduser()

    @classmethod
    def save(cls):
        os.makedirs(os.path.dirname(cls.config_file), exist_ok=True)
        conf_obj = {"testnode_count": cls.args.testnode_count}
        cls.config_file.write_text(yaml.safe_dump(conf_obj))

    @classmethod
    def load(cls):
        if cls.config_file.exists():
            obj = yaml.safe_load(cls.config_file.read_text())
            for k, v in obj.items():
                setattr(cls.args, k, v)
        return cls.args
