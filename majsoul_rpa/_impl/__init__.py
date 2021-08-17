#!/usr/bin/env python3

import re
import datetime
from pathlib import Path
from io import BytesIO
import subprocess
import json
import base64
from typing import (Optional, Union, Tuple, Iterable, )
import yaml
import numpy
import PIL.Image
from PIL.Image import Image
import cv2
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
import pygetwindow
import pyautogui
import redis
from google.protobuf.message_factory import MessageFactory
import google.protobuf.json_format
from majsoul_rpa._impl import mahjongsoul_pb2


Message = Tuple[str, str, object, object, datetime.datetime]


class Redis(object):
    def __init__(self, host='redis', port=6379):
        self.__redis = redis.Redis(host, port)

        self.__message_type_map = {}
        for sdesc in mahjongsoul_pb2.DESCRIPTOR.services_by_name.values():
            for mdesc in sdesc.methods:
                self.__message_type_map['.' + mdesc.full_name] \
                    = (MessageFactory().GetPrototype(mdesc.input_type),
                    MessageFactory().GetPrototype(mdesc.output_type))
        for tdesc in mahjongsoul_pb2.DESCRIPTOR.message_types_by_name.values():
            self.__message_type_map['.' + tdesc.full_name] \
                = (MessageFactory().GetPrototype(tdesc), None)

        self.__account_id = None

    # account id が取得できる WebSocket メッセージ一覧
    __ACCOUNT_ID_MESSAGES = {
        '.lq.Lobby.oauth2Login': ['account_id'],
        '.lq.Lobby.createRoom': ['room', 'owner_id']
    }

    def dequeue_message(self, timeout: float=0.0) -> Optional[Message]:
        if timeout == 0.0:
            message: Optional[bytes] = self.__redis.lpop('message_queue')
        else:
            message: Optional[bytes] = self.__redis.blpop(
                'message_queue', timeout)
            if message is not None:
                _, message = message
        if message is None:
            return None
        message = message.decode('UTF-8')
        message = json.loads(message)
        request_direction: str = message['request_direction']
        request: str = message['request']
        response: Optional[str] = message['response']
        timestamp: float = message['timestamp']

        # JSON 化するためにエンコードしていたデータをデコードする．
        request = base64.b64decode(request)
        if response is not None:
            response = base64.b64decode(response)
        timestamp = datetime.datetime.fromtimestamp(
            timestamp, datetime.timezone.utc)

        def _unwrap_message(message) -> Tuple[str, bytes]:
            wrapper = mahjongsoul_pb2.Wrapper()
            wrapper.ParseFromString(message)
            return (wrapper.name, wrapper.data)

        if request[0] == 1:
            # レスポンスが必要無いリクエストメッセージでメッセージ番号の
            # 2バイトが無い．
            name, request = _unwrap_message(request[1:])
        elif request[0] == 2:
            # 対応するレスポンスメッセージが存在するリクエストメッセージで，
            # メッセージ番号を格納するための2バイトが存在し，また，
            # レスポンスメッセージのパースのために名前を取り出す必要がある．
            name, request = _unwrap_message(request[3:])
        else:
            raise RuntimeError(f'{request[0]}: unknown request type.')

        if response is not None:
            if response[0] != 3:
                raise RuntimeError(f'{response[0]}: unknown response type.')
            _, response = _unwrap_message(response[3:])
            if _ != '':
                raise RuntimeError(f'{_}: unknown response name.')

        # Protocol Buffers メッセージを JSONizable object 形式に変換する．
        def _jsonize(name: str, data: bytes, is_response: bool) -> object:
            if is_response:
                try:
                    parser = self.__message_type_map[name][1]()
                except IndexError as e:
                    proc = subprocess.run(
                        ['protoc', '--decode_raw'], input=data,
                        capture_output=True)
                    rc = proc.returncode
                    stdout = proc.stdout.decode('UTF-8')
                    stderr = proc.stderr.decode('UTF-8')
                    raise RuntimeError(f'''A new API found:
  name: {name}
  data: {data}

===============================
Output of `protoc --decode_raw`
===============================
{stdout}''')
            else:
                try:
                    parser = self.__message_type_map[name][0]()
                except KeyError as e:
                    proc = subprocess.run(
                        ['protoc', '--decode_raw'], input=data,
                        capture_output=True)
                    rc = proc.returncode
                    stdout = proc.stdout.decode('UTF-8')
                    stderr = proc.stderr.decode('UTF-8')
                    raise RuntimeError(f'''A new API found:
  name: {name}
  data: {data}

===============================
Output of `protoc --decode_raw`
===============================
{stdout}''')
            parser.ParseFromString(data)

            jsonized = google.protobuf.json_format.MessageToDict(
                parser, including_default_value_fields=True,
                preserving_proto_field_name=True)
            return jsonized

        request = _jsonize(name, request, False)
        if response is not None:
            response = _jsonize(name, response, True)

        # account id が載っているメッセージなら account id を抽出する．
        if name in Redis.__ACCOUNT_ID_MESSAGES:
            if response is None:
                raise RuntimeError('Message without any response.')
            account_id = response
            keys = Redis.__ACCOUNT_ID_MESSAGES[name]
            for key in keys:
                if key not in account_id:
                    raise RuntimeError(
                        f'''{name}: {key}: Could not find account id field:
{response}''')
                account_id = account_id[key]
            if self.__account_id is None:
                self.__account_id = account_id
            elif account_id != self.__account_id:
                raise RuntimeError('Inconsistent account IDs.')

        return (request_direction, name, request, response, timestamp)

    def get_account_id(self) -> Optional[int]:
        return self.__account_id


def pil2opencv(image: Image) -> numpy.ndarray:
    if image.getbands() == ('R', 'G', 'B'):
        image = numpy.array(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    elif image.getbands() == ('R', 'G', 'B', 'A'):
        image = numpy.array(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    else:
        raise RuntimeError(f'{image.getbands()}: An unknown bands.')
    return image


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

    def click_region(self) -> None:
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
        self.__driver.get('https://game.mahjongsoul.com/')

    def fullscreen(self) -> None:
        self.__driver.fullscreen_window()

    def write(self, message: str, interval) -> None:
        pyautogui.write(message, interval=interval)

    def press(self, keys: Union[str, Iterable[str]]) -> None:
        pyautogui.press(keys)

    def press_hotkey(self, *args: str) -> None:
        pyautogui.hotkey(*args)

    def click_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0) -> None:
        x, y = _get_random_point_in_region(left, top, width, height, edge_sigma)
        pyautogui.click(x, y)

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

    def click_region(
        self, left: int, top: int, width: int, height: int,
        edge_sigma: float=2.0) -> None:
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


class Template(object):
    def __init__(
        self, path: Path, *, left: int=0, top: int=0, width: int=1920,
        height: int=1080, threshold: float=0.99) -> None:
        self.__path = path
        self.__left = left
        self.__top = top
        self.__width = width
        self.__height = height
        self.__threshold = threshold

    @staticmethod
    def open(name_or_path: Union[str, Path]) -> 'Template':
        if isinstance(name_or_path, str):
            if not Path(f'{name_or_path}.yaml').exists():
                if Path(f'{name_or_path}.png').exists():
                    return Template(Path(f'{name_or_path}.png'))
                if name_or_path.endswith('.png'):
                    return Template(Path(f'{name_or_path}'))
                if not name_or_path.endswith('.yaml'):
                    raise ValueError(f'{name_or_path}: an invalid template.')
                path = Path(name_or_path)
            else:
                path = Path(f'{name_or_path}.yaml')
        else:
            path = name_or_path
        if not path.exists():
            raise ValueError(f'{path}: does not exist.')
        if str(path).endswith('.png'):
            return Template(path)

        png_path = Path(re.sub('\\.yaml$', '.png', str(path)))
        if not png_path.exists():
            raise RuntimeError(f'{png_path}: does not exist.')

        with open(path) as f:
            config = yaml.load(f, Loader=yaml.Loader)
        return Template(png_path, **config)

    def best_template_match(self, screenshot: Image) -> Tuple[int, int, float]:
        box = (
            self.__left, self.__top,
            self.__left + self.__width, self.__top + self.__height)
        image = screenshot.crop(box=box)
        image = pil2opencv(image)

        template = PIL.Image.open(self.__path)
        template = pil2opencv(template)

        if template.shape[0] == 0:
            raise ValueError('The height of the template is equal to 0.')
        if image.shape[0] < template.shape[0]:
            raise ValueError(
                f"The height of the screenshot ({image.shape[0]}) is smaller"
                f"than the template's ({template.shape[0]}).")
        if template.shape[1] == 0:
            raise ValueError('The width of the template is equal to 0.')
        if image.shape[1] < template.shape[1]:
            raise ValueError(
                f"The width of the screenshot ({image.shape[1]}) is smaller"
                f" than the template's ({template.shape[1]}).")

        result1: numpy.ndarray = cv2.matchTemplate(
            image, template, cv2.TM_CCOEFF_NORMED)
        result2: numpy.ndarray = cv2.matchTemplate(
            image, template, cv2.TM_SQDIFF_NORMED)

        argmax_x = 0
        argmax_y = 0
        max_score = result1[0, 0]
        for x in range(result1.shape[1]):
            for y in range(result1.shape[0]):
                score = max(result1[y, x], 1.0 - result2[y, x])
                if score > max_score:
                    argmax_x = x
                    argmax_y = y
                    max_score = score

        return (self.__left + argmax_x, self.__top + argmax_y, max_score)

    def match(self, screenshot: Image) -> bool:
        x, y, score = self.best_template_match(screenshot)
        return score >= self.__threshold

    def wait_until(
        self, browser: BrowserBase, deadline: datetime.datetime) -> None:
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                from majsoul_rpa.presentation import Timeout
                Timeout('Timeout', browser.get_screenshot())
            if self.match(browser.get_screenshot()):
                break

    def wait_for(self, browser: BrowserBase, timeout: float) -> None:
        deadline = datetime.datetime.now(datetime.timezone.utc)
        deadline += datetime.timedelta(seconds=timeout)
        self.wait_until(browser, deadline)

    def click(self, browser: BrowserBase, edge_sigma: float=0.2) -> None:
        browser.click_region(
            self.__left, self.__top, self.__width, self.__height, edge_sigma)

    @staticmethod
    def match_one_of(screenshot: Image, templates: Iterable[Image]) -> int:
        for i in range(len(templates)):
            template = Template.open(templates[i])
            if template.match(screenshot):
                return i
        return -1
