#!/usr/bin/env python3
import argparse
import asyncio
import json
import io
import os
import subprocess

from logging import ERROR, INFO
from pathlib import Path
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
    cwd = "."
    exists_cmd: List[str] = []
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

    async def _handle_output(
        self,
        proc_stream: asyncio.StreamReader,
        our_stream: io.StringIO,
        log: bool,
        logLevel: int,
    ):
        while not proc_stream.at_eof():
            line = (await proc_stream.readline()).decode()
            our_stream.write(line)
            line = line.rstrip()
            if line and log:
                logger.log(logLevel, f"{self.name}: {line}")
        our_stream.seek(0)

    async def cmd(
        self,
        args: List[str],
        kwargs: Optional[Dict] = None,
        check: bool = False,
        log_output: bool = False,
    ) -> asyncio.subprocess.Process:
        kwargs = kwargs or {}
        if self.cwd != ".":
            kwargs["cwd"] = str(self.cwd)
        stderr = io.StringIO()
        stdout = io.StringIO()
        proc = await async_cmd(args, kwargs)
        await asyncio.gather(
            proc.wait(),
            self._handle_output(proc.stderr, stderr, log_output, ERROR),
            self._handle_output(proc.stdout, stdout, log_output, INFO),
        )
        if check and proc.returncode != 0:
            if not log_output:
                logger.error(stderr.read())
                stderr.seek(0)
            raise CalledProcessError(cmd=args, returncode=proc.returncode)
        proc.stderr = stderr
        proc.stdout = stdout
        return proc

    def format_cmd(self, args: List):
        vars = {}
        for k in self.cmd_vars:
            v = getattr(self, k, None)
            if v is not None:
                if isinstance(v, Path):
                    v = v.expanduser()
                vars[k] = v
        return [s.format(**vars) for s in args]

    async def apply(self, action: str):
        method = getattr(self, action, None)
        if method is None:
            return
        await method()

    async def inspect(self):
        proc = await self.cmd(self.format_cmd(self.exists_cmd))
        return json.loads(proc.stdout.read())

    async def exists(self, proc: Optional[asyncio.subprocess.Process] = None):
        if not self.exists_cmd:
            return False
        proc = proc or await self.cmd(self.format_cmd(self.exists_cmd), check=False)
        return proc.returncode == 0

    async def create(self):
        if not await self.exists():
            await self.cmd(self.format_cmd(self.create_cmd), check=True)

    async def remove(self):
        await self.cmd(self.format_cmd(self.remove_cmd))

    def __repr__(self):
        param_str = "" if not hasattr(self, "_name") else f'name="{self._name}"'
        return f"{self.__class__.__name__}({param_str})"
