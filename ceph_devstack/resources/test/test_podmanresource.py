import pytest

from unittest.mock import patch

from ceph_devstack.resources import PodmanResource, CalledProcessError


class TestPodmanResource:
    apply_actions = ["create", "remove"]

    @pytest.fixture
    def cls(self):
        return PodmanResource

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

    async def test_apply(self, cls):
        for action in self.apply_actions:
            with patch.object(cls, action):
                obj = cls()
                await obj.apply(action)
                method = getattr(obj, action)
                method.assert_awaited_once()

    async def test_cmd(self, cls):
        with patch("ceph_devstack.resources.async_cmd") as m_async_cmd:
            obj = cls()
            await obj.cmd(["0"])
            m_async_cmd.assert_awaited_once_with(["0"], {}, wait=False)

            m_async_cmd.reset_mock()
            obj = cls()
            await obj.cmd(["1"], kwargs={"foo": "bar"})
            m_async_cmd.assert_awaited_once_with(["1"], {"foo": "bar"}, wait=False)

    async def test_cmd_failed(self, cls):
        obj = cls()
        with pytest.raises(CalledProcessError):
            await obj.cmd(["false"], check=True)
