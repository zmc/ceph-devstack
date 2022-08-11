#!/usr/bin/env python3
import argparse
import asyncio
import logging
import os
import subprocess

from subprocess import CalledProcessError
from typing import List, Dict, Set, Optional

from ceph_devstack.util import async_cmd

logger = logging.getLogger()


class DevStack:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.env = dict()

    def choose_teuthology_branch(self):
        branch = os.environ.get("TEUTHOLOGY_BRANCH", self.get_current_branch())
        self.env["TEUTH_BRANCH"] = branch
        return branch

    def get_current_branch(self, repo_path: str = "."):
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
        )


class PodmanResource:
    create_cmd: List[str] = []
    remove_cmd: List[str] = []
    start_cmd: List[str] = []
    stop_cmd: List[str] = []
    cmd_vars: List[str] = ["name"]
    log: Dict[str, Set[str]] = dict()

    def __init__(self, name: str = ""):
        if name:
            self._name = name

    @property
    def name(self) -> str:
        if hasattr(self, "_name"):
            return self._name
        return self.__class__.__name__.lower()

    async def cmd(
        self,
        args: List[str],
        kwargs: Optional[Dict] = None,
        check: bool = False,
        log_output: bool = False,
    ):
        kwargs = kwargs or dict()
        proc = await async_cmd(args, kwargs, wait=False)
        if proc is None:
            return
        while log_output:
            assert proc.stderr is not None
            stderr_line = await proc.stderr.readline()
            stdout_line = await proc.stderr.readline()
            if stderr_line:
                logger.error(f"{self.name}: {stderr_line.strip()}")
            if stdout_line:
                logger.info(f"{self.name}: {stdout_line.strip()}")
            else:
                break
            await asyncio.sleep(0.01)
        else:
            await proc.wait()
        assert proc.returncode is not None
        if check and proc.returncode != 0:
            assert proc.stderr is not None
            stderr = await proc.stderr.read()
            logger.error(stderr.decode())
            raise CalledProcessError(cmd=args, returncode=proc.returncode)
        return proc

    def format_cmd(self, args: List):
        vars = dict()
        for k in self.cmd_vars:
            v = getattr(self, k, None)
            if v is not None:
                vars[k] = v
        return list(map(lambda s: s.format(**vars), args))

    async def apply(self, action: str, key: str = ""):
        method = getattr(self, action, None)
        if method is None:
            return
        log = self.__class__.log.setdefault(key or self.name, set())
        if action not in log:
            await method()
            log.add(action)

    async def create(self):
        await self.cmd(self.format_cmd(self.create_cmd), check=True)

    async def remove(self):
        await self.cmd(self.format_cmd(self.remove_cmd))

    async def start(self):
        if getattr(self, "start_cmd", None):
            await self.cmd(self.format_cmd(self.start_cmd), check=True)

    async def stop(self):
        if getattr(self, "stop_cmd", None):
            await self.cmd(self.format_cmd(self.stop_cmd))