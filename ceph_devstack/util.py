import asyncio
import logging

from typing import Dict, Optional

from ceph_devstack import Config

logger = logging.getLogger()


async def async_cmd(args, kwargs: Optional[Dict] = None, wait=True):
    kwargs = kwargs or dict()
    logger.debug(" ".join(args))
    if Config.args.dry_run:
        logger.info(args)
        return
    proc = await asyncio.create_subprocess_exec(*args, **kwargs)
    if wait:
        await proc.wait()
    return proc
