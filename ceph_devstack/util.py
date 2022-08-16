import asyncio
import os

from typing import Dict, Optional

from ceph_devstack import Config, logger


async def async_cmd(args, kwargs: Optional[Dict] = None, wait=True):
    kwargs = kwargs or {}
    kwargs.update(
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logger.debug(" ".join(args))
    if Config.args.dry_run:
        logger.info(args)
        return
    env = os.environ | (kwargs.pop("env", None) or {})
    proc = await asyncio.create_subprocess_exec(*args, **kwargs, env=env)
    if wait:
        await proc.wait()
    return proc
