import argparse
import logging

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
        default="/tmp/ceph-devstack",
        help="Store temporary data e.g. disk images here",
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
