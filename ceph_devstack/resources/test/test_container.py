import json
import pytest

from unittest.mock import patch, AsyncMock, Mock

from ceph_devstack.resources.container import Container
from ceph_devstack.resources.test.test_podmanresource import (
    TestPodmanResource as _TestPodmanResource,
)


class TestContainer(_TestPodmanResource):
    apply_actions = ["build", "create", "start", "stop", "remove"]

    @pytest.fixture
    def cls(self):
        return Container

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
            m_decode = Mock()
            m_decode.return_value = json.dumps(output_obj)
            m_read = AsyncMock(return_value=Mock(decode=m_decode))
            m_stdout = Mock(read=m_read)
            obj.cmd.return_value = AsyncMock(stdout=m_stdout, returncode=0)
            assert await obj.is_running() is True

    async def test_is_running_no_bc_status(self, cls):
        with patch.object(cls, "cmd"):
            obj = cls()
            output_obj = [{"State": {"Status": "crashed"}}]
            m_decode = Mock()
            m_decode.return_value = json.dumps(output_obj)
            m_read = AsyncMock(return_value=Mock(decode=m_decode))
            m_stdout = Mock(read=m_read)
            obj.cmd.return_value = AsyncMock(stdout=m_stdout, returncode=0)
            assert await obj.is_running() is False

    async def test_is_running_no_bc_dne(self, cls):
        with patch.object(cls, "cmd"):
            obj = cls()
            obj.cmd.return_value = AsyncMock(returncode=1)
            assert await obj.is_running() is False