import argparse


class Config:
    __slots__ = ["args"]
    args: argparse.Namespace
    native_overlayfs: bool = True
