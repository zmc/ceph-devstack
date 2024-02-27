import asyncio
import logging
import sys
import yaml

from pathlib import Path

from ceph_devstack import config, logger, parse_args, VERBOSE
from ceph_devstack.requirements import check_requirements
from ceph_devstack.resources.ceph import CephDevStack


def main():
    args = parse_args(sys.argv[1:])
    config.load(args.config_file)
    if args.verbose:
        for handler in logging.getLogger("root").handlers:
            if not isinstance(handler, logging.FileHandler):
                handler.setLevel(VERBOSE)
    if args.command == "show-conf":
        print(yaml.safe_dump(config))
        return
    config["args"] = vars(args)
    data_path = Path(config["data_dir"]).expanduser()
    data_path.mkdir(parents=True, exist_ok=True)
    obj = CephDevStack()

    async def run():
        if not await asyncio.gather(
            check_requirements(),
            obj.check_requirements(),
        ):
            logger.error("Requirements not met!")
            sys.exit(1)
        if args.command == "doctor":
            return
        await obj.apply(args.command)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.debug("Exiting!")
