import json
import pytest

from unittest.mock import patch, AsyncMock, Mock

from ceph_devstack import config
from ceph_devstack.resources.container import Container
from ceph_devstack.resources.test.test_podmanresource import (
    TestPodmanResource as _TestPodmanResource,
)


class TestContainer(_TestPodmanResource):
    @pytest.fixture(scope="class")
    def cls(self):
        return Container

    @pytest.fixture(
        scope="class", params=["build", "create", "start", "stop", "remove"]
    )
    def action(self, request):
        return request.param

    def setup_method(self):
        config["containers"]["container"] = {"image": "example.com/image:latest"}

    @pytest.mark.parametrize("rc,res", ([0, True], [1, False]))
    async def test_exists_yes(self, cls, rc, res):
        with patch.object(cls, "cmd"):
            obj = cls()
            obj.cmd.return_value = AsyncMock(returncode=rc)
            assert await obj.exists() is res

    async def test_is_running_yes(self, cls):
        with patch.object(cls, "cmd"):
            obj = cls()
            output_obj = [{"State": {"Status": "running"}}]
            m_read = Mock(return_value=json.dumps(output_obj))
            m_stdout = Mock(read=m_read)
            obj.cmd.return_value = AsyncMock(
                stdout=m_stdout,
                returncode=0,
                wait=lambda: 0,
            )
            assert await obj.is_running() is True

    async def test_is_running_no_bc_status(self, cls):
        with patch.object(cls, "cmd"):
            obj = cls()
            output_obj = [{"State": {"Status": "crashed"}}]
            m_read = Mock(return_value=json.dumps(output_obj))
            m_stdout = Mock(read=m_read)
            obj.cmd.return_value = AsyncMock(
                stdout=m_stdout,
                returncode=0,
                wait=lambda: 0,
            )
            assert await obj.is_running() is False

    async def test_is_running_no_bc_dne(self, cls):
        with patch.object(cls, "cmd"):
            obj = cls()
            obj.cmd.return_value = AsyncMock(returncode=1)
            assert await obj.is_running() is False

    async def test_empty_cmd_skips_action(self, cls, action):
        with patch.object(cls, "cmd"):
            obj = cls()
            setattr(obj, f"{action}_cmd", [])
            await getattr(obj, action)()
            obj.cmd.assert_not_awaited()
