import os
import io
import contextlib
import tempfile
import random as rd
from datetime import datetime, timedelta

from ceph_devstack import config
from ceph_devstack.resources.ceph import CephDevStack


class TestDevStack:
    # ceph-devstack logs : returns teuthology.log of latest run
    # ceph-devstack logs : display message to pick job id if there is more than one job
    # ceph-devstack logs -j <job-id> : display content of given job
    # ceph-devstack logs -r <run-name> : display content on provided run name
    # cepth-devstack logs --locate : show filepath instead one its content
    async def test_logs_command_display_log_file_of_latest_run(self):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()
            content = "custom log content"
            now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            forty_days_ago = (datetime.now() - timedelta(days=40)).strftime(
                "%Y-%m-%dT%H-%M-%S"
            )

            self.create_logfile(data_dir, timestamp=now, content=content)
            self.create_logfile(data_dir, timestamp=forty_days_ago)

            with contextlib.redirect_stdout(f):
                devstack = CephDevStack()
                await devstack.logs()
            assert content in f.getvalue()

    async def test_logs_command_display_message_to_pick_job_id_if_more_than_one_job(
        self,
    ):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()
            content = "log message"
            now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

            self.create_logfile(
                data_dir, timestamp=now, test_type="ceph", job_id="1", content=content
            )
            self.create_logfile(
                data_dir, timestamp=now, test_type="ceph", job_id="2", content=content
            )

            with contextlib.redirect_stdout(f):
                devstack = CephDevStack()
                await devstack.logs()
            assert "please pick a job id" in f.getvalue()

    async def test_logs_command_display_log_file_of_given_job_id(self):
        with tempfile.TemporaryDirectory() as data_dir:
            config["data_dir"] = data_dir
            f = io.StringIO()
            content = "custom log message"
            now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

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
            now = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            three_days_ago = (datetime.now() - timedelta(days=3)).strftime(
                "%Y-%m-%dT%H-%M-%S"
            )

            self.create_logfile(
                data_dir,
                timestamp=now,
            )
            run_name = self.create_logfile(
                data_dir,
                timestamp=three_days_ago,
                content=content,
            )

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
                "%Y-%m-%dT%H-%M-%S"
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

        run_name = f"{timestamp}_{test_type}_master_{job_id}"
        log_dir = f"{data_dir}/{run_name}/{job_id}"

        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/teuthology.log"
        with open(log_file, "w") as f:
            f.write(content)
        return log_file
