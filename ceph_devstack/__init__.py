import argparse
import logging.config
import tomlkit
import tomlkit.items
import tomlkit.exceptions

from pathlib import Path
from typing import List, Optional, Union


VERBOSE = 15
logging.addLevelName(15, "VERBOSE")
logging.config.fileConfig(Path(__file__).parent / "logging.conf")
logger = logging.getLogger("ceph-devstack")

PROJECT_ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = Path("~/.config/ceph-devstack/config.toml")


def parse_args(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Instead of running commands, print them",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Be more verbose",
    )
    parser.add_argument(
        "-c",
        "--config-file",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the ceph-devstack config file",
    )
    subparsers = parser.add_subparsers(dest="command")
    parser_config = subparsers.add_parser("config", help="Get or set config items")
    subparsers_config = parser_config.add_subparsers(dest="config_op")
    subparsers_config.add_parser("dump", help="show the configuration")
    parser_config_get = subparsers_config.add_parser("get")
    parser_config_get.add_argument("name")
    parser_config_set = subparsers_config.add_parser("set")
    parser_config_set.add_argument("name")
    parser_config_set.add_argument("value")
    parser_doc = subparsers.add_parser(
        "doctor", help="Check that the system meets requirements"
    )
    parser_doc.add_argument(
        "--fix",
        action="store_true",
        default=False,
        help="Apply suggested fixes for issues found",
    )
    parser_pull = subparsers.add_parser("pull", help="Pull container images")
    parser_pull.add_argument(
        "image",
        nargs="*",
        help="Specific image(s) to pull",
    )
    parser_build = subparsers.add_parser("build", help="Build container images")
    parser_build.add_argument(
        "image",
        nargs="*",
        help="Specific image(s) to build",
    )
    parser_create = subparsers.add_parser(
        "create",
        help="Create the cluster",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_create.add_argument(
        "-b",
        "--build",
        action="store_true",
        default=False,
        help="Build images before creating",
    )
    parser_create.add_argument(
        "-w",
        "--wait",
        action="store_true",
        default=False,
        help="Leave the cluster running - and don't auto-schedule anything",
    )

    parser_show_log = subparsers.add_parser("show-log", help="Show test logs")
    parser_show_log.add_argument(
        "-f",
        "--filepath",
        action="store_true",
        default=False,
        help="Output just the full path of the logfile instead of its content"
    )
    subparsers.add_parser("remove", help="Destroy the cluster")
    subparsers.add_parser("start", help="Start the cluster")
    subparsers.add_parser("stop", help="Stop the cluster")
    subparsers.add_parser(
        "watch", help="Monitor the cluster, recreating containers as necessary"
    )
    parser_wait = subparsers.add_parser(
        "wait",
        help="Wait for the specified container to exit. Exit with its exit code.",
    )
    parser_wait.add_argument(
        "container",
        help="The container to wait for",
    )
    return parser.parse_args(args)


def deep_merge(*maps):
    result = {}
    for map in maps:
        for k, v in map.items():
            if isinstance(v, dict):
                v = deep_merge(result.get(k, {}), v)
            result[k] = v
    return result


class Config(dict):
    __slots__ = ["user_obj", "user_path"]

    def load(self, config_path: Optional[Path] = None):
        parsed = tomlkit.parse((Path(__file__).parent / "config.toml").read_text())
        self.update(parsed)
        if config_path:
            self.user_path = config_path.expanduser()
            if self.user_path.exists():
                self.user_obj: dict = tomlkit.parse(self.user_path.read_text()) or {}
                self.update(deep_merge(config, self.user_obj))
            elif self.user_path != DEFAULT_CONFIG_PATH.expanduser():
                raise OSError(f"Config file at {self.user_path} not found!")
            else:
                self.user_obj = {}

    def dump(self):
        return tomlkit.dumps(self)

    def get_value(self, name: str) -> str:
        path = name.split(".")
        obj = config
        i = 0
        while i < len(path):
            sub_path = path[i]
            try:
                obj = obj[sub_path]
            except KeyError:
                logger.error(f"{name} not found in config")
                raise
            i += 1
        if isinstance(obj, (str, int, bool)):
            return str(obj)
        return tomlkit.dumps(obj).strip()

    def set_value(self, name: str, value: str):
        path = name.split(".")
        obj = self.user_obj
        i = 0
        last_index = len(path) - 1
        item: Union[tomlkit.items.Item, str] = value
        try:
            item = tomlkit.value(item)
        except tomlkit.exceptions.UnexpectedCharError:
            pass
        except tomlkit.exceptions.InternalParserError:
            pass
        while i <= last_index:
            if i < last_index:
                obj = obj.setdefault(path[i], {})
            elif i == last_index:
                obj[path[i]] = item
                self.update(self.user_obj)
                self.user_path.parent.mkdir(exist_ok=True)
                self.user_path.write_text(tomlkit.dumps(self.user_obj).strip())
            i += 1


config = Config()
config.load()
