#!/usr/bin/env python3

import datetime
from majsoul_rpa._impl.mahjongsoul_pb2 import Room
from pathlib import Path
import time
import uuid
from typing import (Optional, Union, Tuple, Iterable,)
import yaml
import docker
from PIL.Image import Image
from majsoul_rpa.common import Player
from majsoul_rpa.presentation.presentation_base import (
    InconsistentMessage, StalePresentation, PresentationBase,
    PresentationNotUpdated, Timeout, PresentationNotDetected)
from majsoul_rpa._impl import (Redis, BrowserBase, DesktopBrowser, RemoteBrowser)


class RPA(object):
    def __init__(
        self, proxy_port: Optional[int]=8080,
        redis_port: Optional[int]=None) -> None:
        # Docker Desktop for Windows でデスクトップモードを動かすと，
        # Docker Desktop for Windows の制約上， Redis コンテナに
        # 接続できないので， redis_port を指定して expose する必要がある．
        self.__id = uuid.uuid4()
        self.__redis_port = redis_port
        self.__proxy_port = proxy_port
        self.__docker_client = None
        self.__docker_network = None
        self.__redis_container = None
        self.__mitmproxy_container = None
        self.__browser = None
        self.__redis = None

    def __enter__(self) -> 'RPA':
        # Docker クライアントを取得．
        self.__docker_client = docker.from_env()

        # Docker ネットワークを構築．
        network_name = f'majsoul-rpa-{self.__id}'
        self.__docker_network = self.__docker_client.networks.create(
            network_name, check_duplicate=True)

        # Redis コンテナを走らせる．
        if self.__redis_port is None:
            self.__redis_container = self.__docker_client.containers.run(
                'redis', auto_remove=True, detach=True, hostname='redis',
                network=network_name)
        else:
            self.__redis_container = self.__docker_client.containers.run(
                'redis', auto_remove=True, detach=True, hostname='redis',
                network=network_name, ports={'6379/tcp': self.__redis_port})

        # Network sniffering コンテナを走らせる．
        if self.__proxy_port is None:
            self.__mitmproxy_container = self.__docker_client.containers.run(
                'majsoul-rpa-sniffer-headless', auto_remove=True, detach=True,
                hostname='sniffer', network=network_name)
        else:
            self.__mitmproxy_container = self.__docker_client.containers.run(
                'majsoul-rpa-sniffer-desktop', auto_remove=True, detach=True,
                hostname='sniffer', network=network_name,
                ports={'8080/tcp': self.__proxy_port})

        # ブラウザ操作を抽象化するクラスインスタンスを構築．
        if self.__proxy_port is None:
            self.__browser = RemoteBrowser(self.__redis_port)
        else:
            self.__browser = DesktopBrowser(self.__proxy_port)

        # Redis クライアントを抽象化するクラスインスタンスを構築．
        if self.__redis_port is None:
            self.__redis = Redis('redis')
        else:
            self.__redis = Redis('localhost', self.__redis_port)

        # ブラウザをフルスクリーン化
        time.sleep(1.0)
        self.__browser.fullscreen()

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.__redis = None
        if self.__browser is not None:
            self.__browser.close()
            self.__browser = None
        if self.__mitmproxy_container is not None:
            self.__mitmproxy_container.stop()
            self.__mitmproxy_container = None
        if self.__redis_container is not None:
            self.__redis_container.stop()
            self.__redis_container = None
        if self.__docker_network is not None:
            self.__docker_network.remove()
            self.__docker_network = None
        if self.__docker_client is not None:
            self.__docker_client.close()
            self.__docker_client = None

    def get_account_id(self) -> int:
        if self.__redis.account_id is None:
            raise RuntimeError('`account_id` has not been fetched yet.')
        return self.__redis.account_id

    def get_screenshot(self) -> Image:
        return self.__browser.get_screenshot()

    def _get_redis(self) -> Redis:
        return self.__redis

    def _get_browser(self) -> BrowserBase:
        return self.__browser

    def activate_browser(self) -> None:
        self.__browser.activate()

    def _write(self, message: str, interval=0.1) -> None:
        self.__browser.write(message, interval=interval)

    def _press(self, keys: Union[str, Iterable[str]]):
        self.__browser.press(keys)

    def _press_hotkey(self, *args: str):
        self.__browser.press_hotkey(*args)

    def _move_to_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        self.__browser.move_to_region(
            left, top, width, height, edge_sigma=edge_sigma, warp=warp)

    def _scroll(self, clicks: int) -> None:
        self.__browser.scroll(clicks)

    def _click_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        self.__browser.click_region(
            left, top, width, height, edge_sigma=edge_sigma, warp=warp)

    def _click_template(self, name_or_path: Union[str, Path]) -> None:
        if isinstance(name_or_path, Path):
            name_or_path = str(name_or_path)
        if name_or_path.endswith('.yaml'):
            path = Path(name_or_path)
        else:
            path = Path(f'{name_or_path}.yaml')
        if not path.exists():
            raise RuntimeError(f'{path}: does not exist.')
        with open(path) as f:
            data = yaml.load(f, Loader=yaml.Loader)
        left = data['left']
        top = data['top']
        width = data['width']
        height = data['height']
        self._click_region(left, top, width, height)

    def wait(self, timeout: float) -> PresentationBase:
        start_time = datetime.datetime.now(datetime.timezone.utc)
        deadline = start_time + datetime.timedelta(seconds=timeout)

        while True:
            screenshot = self.get_screenshot()

            try:
                from majsoul_rpa.presentation import LoginPresentation
                return LoginPresentation(screenshot)
            except PresentationNotDetected as e:
                pass

            try:
                from majsoul_rpa.presentation import AuthPresentation
                return AuthPresentation(screenshot)
            except PresentationNotDetected as e:
                pass

            try:
                from majsoul_rpa.presentation import HomePresentation
                # `HomePresentation` に遷移している場合で，告知が
                # 表示されているならばそれらを閉じる．
                now = datetime.datetime.now(datetime.timezone.utc)
                HomePresentation._close_notifications(
                    self.__browser, deadline - now)
                now = datetime.datetime.now(datetime.timezone.utc)
                return HomePresentation(
                    screenshot, self.__redis, deadline - now)
            except PresentationNotDetected as e:
                pass

            now = datetime.datetime.now(datetime.timezone.utc)
            if now > deadline:
                raise Timeout('Timeout', self.get_screenshot())
