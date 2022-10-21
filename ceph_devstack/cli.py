import asyncio
import logging
import sys

from ceph_devstack import Config, logger, parse_args
from ceph_devstack.requirements import check_requirements
from ceph_devstack.resources.ceph import CephDevStack


def main():
    args = parse_args(sys.argv[1:])
    Config.args = args
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    Config.load()
    obj = CephDevStack()

    async def run():
        check_requirements()
        if args.command == "doctor":
            return
        await obj.apply(args.command)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.debug("Exiting!")
