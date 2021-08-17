#!/usr/bin/env python3

import subprocess
import sys
from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def _pre_install() -> None:
    subprocess.run(
        ['protoc', '--python_out', '.', 'mahjongsoul.proto'],
        cwd='majsoul_rpa/_impl', stdout=sys.stdout, stderr=sys.stderr,
        text=True, encoding='UTF-8')


def _post_install() -> None:
    subprocess.run(
        ['docker', 'build', '--tag', 'majsoul-rpa-sniffer-desktop', '.'],
        cwd='mitmproxy', stdout=sys.stdout, stderr=sys.stderr, text=True,
        encoding='UTF-8')
    subprocess.run(
        ['docker', 'build', '--tag', 'majsoul-rpa-sniffer-headless', '.'],
        cwd='headless_browser', stdout=sys.stdout, stderr=sys.stderr, text=True,
        encoding='UTF-8')


class DevelopCommand(develop):
    def run(self) -> None:
        _pre_install()
        super(DevelopCommand, self).run()
        _post_install()


class InstallCommand(install):
    def run(self) -> None:
        _pre_install()
        super(InstallCommand, self).run()
        _post_install()


setup(cmdclass={'develop': DevelopCommand, 'install': InstallCommand})
