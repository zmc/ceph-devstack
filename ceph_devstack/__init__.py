import argparse
import logging


logging.basicConfig(
    format="%(levelname)s:%(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("ceph-devstack")


class Config:
    __slots__ = ["args"]
    args: argparse.Namespace
    native_overlayfs: bool = True
