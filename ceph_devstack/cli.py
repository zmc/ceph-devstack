import asyncio
import logging
import sys

from ceph_devstack import Config, logger, parse_args, RequirementsNotMet
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
        try:
            check_requirements()
            obj.check_requirements()
        except RequirementsNotMet as exc:
            logger.error(str(exc))
            sys.exit(1)
        if args.command == "doctor":
            return
        await obj.apply(args.command)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.debug("Exiting!")
