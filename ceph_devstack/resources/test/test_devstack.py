import os
import io
import contextlib
import tempfile
import random as rd
from datetime import datetime, timedelta

import pytest

from ceph_devstack import config
from ceph_devstack.resources.ceph.utils import (
    get_logtimestamp,
    get_most_recent_run,
    get_job_id,
)
from ceph_devstack.resources.ceph.exceptions import TooManyJobsFound
from ceph_devstack.resources.ceph import CephDevStack


class TestDevStack:
    def test_get_logtimestamp(self):
        dirname = "root-2025-03-20_18:34:43-orch:cephadm:smoke-small-main-distro-default-testnode"
        assert get_logtimestamp(dirname) == datetime(2025, 3, 20, 18, 34, 43)

    def test_get_most_recent_run_returns_most_recent_run(self):
        runs = [
            "root-2024-02-07_12:23:43-orch:cephadm:smoke-small-devlop-distro-smithi-testnode",
            "root-2025-02-20_11:23:43-orch:cephadm:smoke-small-devlop-distro-smithi-testnode",
            "root-2025-03-20_18:34:43-orch:cephadm:smoke-small-main-distro-default-testnode",
            "root-2025-01-18_18:34:43-orch:cephadm:smoke-small-main-distro-default-testnode",
        ]
        assert (
            get_most_recent_run(runs)
            == "root-2025-03-20_18:34:43-orch:cephadm:smoke-small-main-distro-default-testnode"
        )

    def test_get_job_id_returns_job_on_unique_job(self):
        jobs = ["97"]
        assert get_job_id(jobs) == "97"

    def test_get_job_id_throws_filenotfound_on_missing_job(self):
        jobs = []
        with pytest.raises(FileNotFoundError):
            get_job_id(jobs)

    def test_get_job_id_throws_toomanyjobsfound_on_more_than_one_job(self):
        jobs = ["1", "2"]
        with pytest.raises(TooManyJobsFound):
            get_job_id(jobs)

    async def test_logs_command_display_log_file_of_latest_run(self):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()
            content = "custom log content"
            now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            forty_days_ago = (datetime.now() - timedelta(days=40)).strftime(
                "%Y-%m-%d_%H:%M:%S"
            )

            self.create_logfile(data_dir, timestamp=now, content=content)
            self.create_logfile(data_dir, timestamp=forty_days_ago)

            with contextlib.redirect_stdout(f):
                devstack = CephDevStack()
                await devstack.logs()
            assert content in f.getvalue()

    async def test_logs_command_display_log_file_of_given_job_id(self):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()
            content = "custom log message"
            now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

            self.create_logfile(
                data_dir,
                timestamp=now,
                test_type="ceph",
                job_id="1",
                content="another log",
            )
            self.create_logfile(
                data_dir, timestamp=now, test_type="ceph", job_id="2", content=content
            )

            with contextlib.redirect_stdout(f):
                devstack = CephDevStack()
                await devstack.logs(job_id="2")
            assert content in f.getvalue()

    async def test_logs_display_content_of_provided_run_name(self):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()
            content = "custom content"
            now = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            three_days_ago = (datetime.now() - timedelta(days=3)).strftime(
                "%Y-%m-%d_%H:%M:%S"
            )

            self.create_logfile(
                data_dir,
                timestamp=now,
            )
            run_name = self.create_logfile(
                data_dir,
                timestamp=three_days_ago,
                content=content,
            ).split("/")[-3]

            with contextlib.redirect_stdout(f):
                devstack = CephDevStack()
                await devstack.logs(run_name=run_name)
            assert content in f.getvalue()

    async def test_logs_locate_display_file_path_instead_of_config(self):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()

            logfile = self.create_logfile(data_dir)
            with contextlib.redirect_stdout(f):
                devstack = CephDevStack()
                await devstack.logs(locate=True)
            assert logfile in f.getvalue()

    def create_logfile(self, data_dir: str, **kwargs):
        parts = {
            "timestamp": (datetime.now() - timedelta(days=rd.randint(1, 100))).strftime(
                "%Y-%m-%d_%H:%M:%S"
            ),
            "test_type": rd.choice(["ceph", "rgw", "rbd", "mds"]),
            "job_id": rd.randint(1, 100),
            "content": "some log data",
            **kwargs,
        }
        timestamp = parts["timestamp"]
        test_type = parts["test_type"]
        job_id = parts["job_id"]
        content = parts["content"]

        run_name = f"root-{timestamp}-orch:cephadm:{test_type}-small-main-distro-default-testnode"
        log_dir = f"{data_dir}/archive/{run_name}/{job_id}"

        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/teuthology.log"
        with open(log_file, "w") as f:
            f.write(content)
        print(log_file)
        return log_file
