import asyncio
import os
import socket

from typing import Dict, Optional

from ceph_devstack import logger


async def async_cmd(args, kwargs: Optional[Dict] = None):
    kwargs = kwargs or {}
    kwargs.update(
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    logger.debug("> " + " ".join(args))
    env = os.environ | (kwargs.pop("env", None) or {})
    proc = await asyncio.create_subprocess_exec(*args, **kwargs, env=env)
    return proc


def get_local_hostname():
    """
    If the value of socket.gethostname() is resolvable to an IP, return that.
    Else, return "localhost"
    """
    name = socket.gethostname()
    try:
        socket.gethostbyname(name)
        return name
    except socket.gaierror:
        return "localhost"
