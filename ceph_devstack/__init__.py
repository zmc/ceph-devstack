import argparse
import logging.config
import yaml

from pathlib import Path, PosixPath
from typing import List, Optional


VERBOSE = 15
logging.addLevelName(15, "VERBOSE")
logging.config.fileConfig("./logging.conf")
logger = logging.getLogger("ceph-devstack")

PROJECT_ROOT = Path(__file__).parent
DEFAULT_CONFIG_PATH = Path("~/.config/ceph-devstack/config.yml")


def represent_path(dumper: yaml.dumper.SafeDumper, data: PosixPath) -> yaml.Node:
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data))


yaml.SafeDumper.add_representer(
    PosixPath,
    represent_path,
)


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
    subparsers.add_parser("remove", help="Destroy the cluster")
    subparsers.add_parser("start", help="Start the cluster")
    subparsers.add_parser("stop", help="Stop the cluster")
    subparsers.add_parser(
        "watch", help="Monitor the cluster, recreating containers as necessary"
    )
    subparsers.add_parser("show-conf", help="show the configuration")
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
    def load(self, config_path: Optional[Path] = None):
        self.update(yaml.safe_load((Path(__file__).parent / "config.yml").read_text()))
        if config_path:
            user_path = config_path.expanduser()
            if user_path.exists():
                user_obj = yaml.safe_load(user_path.read_text())
                self.update(deep_merge(config, user_obj))
            elif user_path != DEFAULT_CONFIG_PATH.expanduser():
                raise OSError(f"Config file at {user_path} not found!")


yaml.SafeDumper.add_representer(
    Config,
    yaml.representer.SafeRepresenter.represent_dict,
)


config = Config()
config.load()
