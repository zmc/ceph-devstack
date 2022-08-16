import argparse
import asyncio
import logging
import sys

from typing import List

from ceph_devstack import Config, logger
from ceph_devstack.requirements import check_requirements
from ceph_devstack.resources.ceph import CephDevStack


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
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
    parser_create = subparsers.add_parser("create", help="Create the cluster")
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
    Config.args = parsed_args
    return parsed_args


def main():
    args = parse_args(sys.argv[1:])
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    obj = CephDevStack()

    async def run():
        await check_requirements()
        await obj.apply(args.command)

    asyncio.run(run())
