#!/usr/bin/env python3
import argparse
import asyncio
import os
import subprocess

from subprocess import CalledProcessError
from typing import List, Dict, Set, Optional

from ceph_devstack import logger
from ceph_devstack.util import async_cmd


class DevStack:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.env: Dict[str, str] = {}

    def choose_teuthology_branch(self):
        branch = os.environ.get("TEUTHOLOGY_BRANCH", self.get_current_branch())
        self.env["TEUTH_BRANCH"] = branch
        return branch

    def get_current_branch(self, repo_path: str = "."):
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=repo_path,
        ).decode()


class PodmanResource:
    create_cmd: List[str] = []
    remove_cmd: List[str] = []
    start_cmd: List[str] = []
    stop_cmd: List[str] = []
    cmd_vars: List[str] = ["name"]
    log: Dict[str, Set[str]] = {}

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
        kwargs = kwargs or {}
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
        vars = {}
        for k in self.cmd_vars:
            v = getattr(self, k, None)
            if v is not None:
                vars[k] = v
        return [s.format(**vars) for s in args]

    async def apply(self, action: str):
        method = getattr(self, action, None)
        if method is None:
            return
        await method()

    async def create(self):
        await self.cmd(self.format_cmd(self.create_cmd), check=True)

    async def remove(self):
        await self.cmd(self.format_cmd(self.remove_cmd))

    def __repr__(self):
        param_str = "" if not hasattr(self, "_name") else f'name="{self._name}"'
        return f"{self.__class__.__name__}({param_str})"
