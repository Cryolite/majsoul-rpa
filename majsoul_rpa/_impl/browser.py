#!/usr/bin/env python3

import math
from io import BytesIO
import time
import json
import base64
from typing import (Tuple, Union, Iterable,)
import PIL.Image
from PIL.Image import Image
import pygetwindow
import pyautogui
import redis
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver


def _get_random_point_in_region(
    left: int, top: int, width: int, height: int,
    edge_sigma: float=0.2) -> Tuple[int, int]:
    import random

    x_mu = left + (width - 1.0) / 2.0
    x_sigma = (x_mu - left) / edge_sigma
    while True:
        x = random.normalvariate(x_mu, x_sigma)
        x = round(x)
        if left <= x and x < left + width:
            break

    y_mu = top + (height - 1.0) / 2.0
    y_sigma = (y_mu - top) / edge_sigma
    while True:
        y = random.normalvariate(y_mu, y_sigma)
        y = round(y)
        if top <= y and y < top + height:
            break

    return (x, y)


class BrowserBase(object):
    def __init__(self) -> None:
        self._window = None

    def fullscreen(self) -> None:
        raise NotImplementedError

    def activate(self) -> None:
        if self._window is None:
            windows = []
            for w in pygetwindow.getAllWindows():
                if w.title.startswith(
                    '雀魂 -じゃんたま-| 麻雀を無料で気軽に'):
                    windows.append(w)
            if len(windows) == 0:
                raise RuntimeError('No window for Mahjong Soul is found.')
            if len(windows) > 1:
                raise RuntimeError(
                    'Multiple windows for Mahjong Soul are found.')
            self._window = windows[0]
        self._window.activate()

    def write(self, message: str, interval: float) -> None:
        raise NotImplementedError

    def press(self, keys: Union[str, Iterable[str]]) -> None:
        raise NotImplementedError

    def press_hotkey(self, *args: str) -> None:
        raise NotImplementedError

    def move_to_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        raise NotImplementedError

    def click_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        raise NotImplementedError

    def get_screenshot(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float) -> Image:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class DesktopBrowser(BrowserBase):
    def __init__(self, proxy_port: int) -> None:
        super(DesktopBrowser, self).__init__()

        options = webdriver.ChromeOptions()
        options.add_argument(f'--proxy-server=http://localhost:{proxy_port}')
        options.add_argument('--ignore-certificate-errors')
        options.add_experimental_option(
            'excludeSwitches', ['enable-automation'])
        self.__driver = WebDriver(options=options)
        time.sleep(1.0)
        self.__driver.get('https://game.mahjongsoul.com/')

    def fullscreen(self) -> None:
        self.__driver.fullscreen_window()

    def write(self, message: str, interval) -> None:
        pyautogui.write(message, interval=interval)

    def press(self, keys: Union[str, Iterable[str]]) -> None:
        pyautogui.press(keys)

    def press_hotkey(self, *args: str) -> None:
        pyautogui.hotkey(*args)

    def move_to_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        x, y = pyautogui.position()
        if left <= x and x < left + width and top <= y and y < top + height:
            return

        xx, yy = _get_random_point_in_region(
            left, top, width, height, edge_sigma=edge_sigma)
        if warp:
            duration = 0.0
        else:
            distance = math.sqrt((xx - x) ** 2.0 + (yy - y) ** 2.0)
            duration = 0.1 + 0.4 * math.sqrt(distance / 1980.0)
        pyautogui.moveTo(xx, yy, duration, pyautogui.easeInOutSine)

    def click_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        self.move_to_region(
            left, top, width, height, edge_sigma=edge_sigma, warp=warp)
        pyautogui.click()

    def get_screenshot(self) -> Image:
        png = self.__driver.get_screenshot_as_png()
        return PIL.Image.open(BytesIO(png))

    def close(self) -> None:
        self.__driver.close()
        self.__driver = None


class RemoteBrowser(BrowserBase):
    def __init__(self, port) -> None:
        super(RemoteBrowser, self).__init__()
        if port is None:
            self.__redis = redis.Redis('redis')
        else:
            self.__redis = redis.Redis('localhost', port)

    def __communicate(self, message: object) -> object:
        message = json.dumps(message, separators=(',', ':'))
        message = message.encode('UTF-8')
        if self.__redis.llen('browser_request') > 0:
            raise RuntimeError(
                'Failed to send a message to the remote browser.')
        if self.__redis.lpush('browser_request', message) != 1:
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

        _, message = self.__redis.brpop('browser_response')
        message = message.decode('UTF-8')
        message = json.loads(message)
        return message

    def fullscreen(self) -> None:
        request = {'type': 'fullscreen'}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

    def activate(self) -> None:
        pass

    def write(self, message: str, interval: float) -> None:
        request = {'type': 'write', 'message': message, 'interval': interval}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

    def press(self, keys: Union[str, Iterable[str]]) -> None:
        if not isinstance(keys, str):
            keys = [k for k in keys]
        request = {'type': 'press', 'keys': keys}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

    def press_hotkey(self, *args: str) -> None:
        request = {'type': 'press_hotkey', 'args': [a for a in args]}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

    def move_to_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        x, y = _get_random_point_in_region(left, top, width, height, edge_sigma)
        request = {'type': 'move', 'x': x, 'y': y}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

    def click_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0, warp: bool=False) -> None:
        x, y = _get_random_point_in_region(left, top, width, height, edge_sigma)
        request = {'type': 'click', 'x': x, 'y': y}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')

    def get_screenshot(self) -> Image:
        request = {'type': 'get_screenshot'}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')
        data: str = response['data']
        data = base64.b64decode(data)
        image = PIL.Image.open(BytesIO(data))
        return image

    def close(self) -> None:
        request = {'type': 'close'}
        response = self.__communicate(request)
        if response['result'] != 'O.K.':
            raise RuntimeError(
                'Failed to send a message to the remote browser.')
