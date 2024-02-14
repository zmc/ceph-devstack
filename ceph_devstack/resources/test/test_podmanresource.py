import pytest

from subprocess import CalledProcessError
from unittest.mock import patch, Mock

from ceph_devstack.resources import PodmanResource


class TestPodmanResource:
    @pytest.fixture(scope="class")
    def cls(self):
        return PodmanResource

    @pytest.fixture(scope="class", params=["create", "remove"])
    def action(self, request):
        return request.param

    def test_name(self, cls):
        obj = cls()
        assert obj.name == cls.__name__.lower()
        obj = cls(name="foo")
        assert obj.name == "foo"

    def test_format_cmd(self, cls):
        obj = cls(name="pr")
        assert "name" in obj.cmd_vars
        res = obj.format_cmd(["foo", "{name}", "bar", "x{name}x"])
        assert res == ["foo", "pr", "bar", "xprx"]

    def test_repr(self, cls):
        obj = cls()
        class_name = cls.__name__
        assert repr(obj) == f"{class_name}()"
        obj = cls(name="foo")
        assert repr(obj) == f'{class_name}(name="foo")'

    async def test_apply(self, cls, action):
        with patch.object(cls, action):
            obj = cls()
            await obj.apply(action)
            method = getattr(obj, action)
            method.assert_awaited_once()

    async def test_cmd(self, cls):
        with patch("ceph_devstack.host.host.arun") as m_arun:
            # at_eof() is not async, so the below lines avoid this warning:
            # RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
            m_arun.return_value.stderr.at_eof = Mock()
            m_arun.return_value.stdout.at_eof = Mock()
            obj = cls()
            await obj.cmd(["0"])
            m_arun.assert_awaited_once_with(["0"])

    async def test_cmd_failed(self, cls):
        obj = cls()
        with pytest.raises(CalledProcessError):
            await obj.cmd(["false"], check=True)
