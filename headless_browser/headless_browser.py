#!/usr/bin/env python3

from io import BytesIO
import time
import subprocess
import json
import base64
import redis
import PIL.Image
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.proxy import Proxy
from selenium.webdriver.common.desired_capabilities \
    import DesiredCapabilities
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver import ActionChains
from selenium.webdriver import Chrome


_KEY_MAP = {
    'add': Keys.ADD,
    'alt': Keys.ALT,
    #'': Keys.ARROW_DOWN,
    #'': Keys.ARROW_LEFT,
    #'': Keys.ARROW_RIGHT,
    #'': Keys.ARROW_UP,
    'backspace': Keys.BACKSPACE,
    #'': Keys.CANCEL,
    'clear': Keys.CLEAR,
    'command': Keys.COMMAND,
    'ctrl': Keys.CONTROL,
    'decimal': Keys.DECIMAL,
    'del': Keys.DELETE,
    'delete': Keys.DELETE,
    'divide': Keys.DIVIDE,
    'down': Keys.DOWN,
    'end': Keys.END,
    'enter': Keys.ENTER,
    #'': Keys.EQUALS,
    'esc': Keys.ESCAPE,
    'escape': Keys.ESCAPE,
    'f1': Keys.F1,
    'f2': Keys.F2,
    'f3': Keys.F3,
    'f4': Keys.F4,
    'f5': Keys.F5,
    'f6': Keys.F6,
    'f7': Keys.F7,
    'f8': Keys.F8,
    'f9': Keys.F9,
    'f10': Keys.F10,
    'f11': Keys.F11,
    'f12': Keys.F12,
    'help': Keys.HELP,
    'home': Keys.HOME,
    'insert': Keys.INSERT,
    'left': Keys.LEFT,
    'altleft': Keys.LEFT_ALT,
    'ctrlleft': Keys.LEFT_CONTROL,
    'shiftleft': Keys.LEFT_SHIFT,
    #'': Keys.META,
    'multiply': Keys.MULTIPLY,
    #'': Keys.NULL,
    'num0': Keys.NUMPAD0,
    'num1': Keys.NUMPAD1,
    'num2': Keys.NUMPAD2,
    'num3': Keys.NUMPAD3,
    'num4': Keys.NUMPAD4,
    'num5': Keys.NUMPAD5,
    'num6': Keys.NUMPAD6,
    'num7': Keys.NUMPAD7,
    'num8': Keys.NUMPAD8,
    'num9': Keys.NUMPAD9,
    'pagedown': Keys.PAGE_DOWN,
    'pgdn': Keys.PAGE_DOWN,
    'pageup': Keys.PAGE_UP,
    'pgup': Keys.PAGE_UP,
    'pause': Keys.PAUSE,
    'return': Keys.RETURN,
    'right': Keys.RIGHT,
    #'': Keys.SEMICOLON,
    'separator': Keys.SEPARATOR,
    'shift': Keys.SHIFT,
    'space': Keys.SPACE,
    'subtract': Keys.SUBTRACT,
    'tab': Keys.TAB,
    'up': Keys.UP,
}


def main(driver) -> None:
    driver.get('https://game.mahjongsoul.com/')
    canvas = WebDriverWait(driver, 60).until(
        ec.visibility_of_element_located((By.ID, 'layaCanvas')))
    redis_ = redis.Redis('redis')

    def respond(message) -> None:
        message = json.dumps(message, separators=(',', ':'))
        message = message.encode('UTF-8')
        redis_.lpush('browser_response', message)

    while True:
        _, message = redis_.brpop('browser_request')
        message = message.decode('UTF-8')
        message = json.loads(message)

        if message['type'] == 'fullscreen':
            driver.fullscreen_window()
            response = {'result': 'O.K.'}
            respond(response)
        elif message['type'] == 'write':
            s = message['message']
            interval = message['interval']
            if s != '':
                ActionChains(driver).send_keys(s[0]).perform()
                for i in range(1, len(s)):
                    time.sleep(interval)
                    ActionChains(driver).send_keys(s[i]).perform()
            response = {'result': 'O.K.'}
            respond(response)
        elif message['type'] == 'press':
            keys = message['keys']
            if isinstance(keys, list):
                ac = ActionChains(driver)
                for key in keys:
                    ac = ac.send_keys(_KEY_MAP[key])
                ac.perform()
            else:
                ActionChains(driver).send_keys(_KEY_MAP[keys]).perform()
            response = {'result': 'O.K.'}
            respond(response)
        elif message['type'] == 'press_hotkey':
            args = message['args']
            if len(args) > 0:
                ac = ActionChains(driver)
                for i in range(len(args) - 1):
                    ac.key_down(_KEY_MAP[args[i]])
                ac.send_keys(args[-1])
                for i in range(len(args) - 1, 0, -1):
                    ac.key_up(_KEY_MAP[args[i - 1]])
            response = {'result': 'O.K.'}
            respond(response)
        elif message['type'] == 'move':
            x = message['x']
            y = message['y']
            ac = ActionChains(driver)
            ac.move_to_element_with_offset(canvas, x, y)
            ac.perform
            response = {'result': 'O.K.'}
            respond(response)
        elif message['type'] == 'click':
            x = message['x']
            y = message['y']
            ac = ActionChains(driver)
            ac.move_to_element_with_offset(canvas, x, y)
            ac.click()
            ac.perform()
            response = {'result': 'O.K.'}
            respond(response)
        elif message['type'] == 'get_screenshot':
            data = driver.get_screenshot_as_png()
            data = base64.b64encode(data)
            data = data.decode('UTF-8')
            response = {'result': 'O.K.', 'data': data}
            respond(response)
        elif message['type'] == 'close':
            driver.close()
            response = {'result': 'O.K.'}
            respond(response)
        else:
            raise RuntimeError(f'{message["type"]}: An unknown message.')


if __name__ == '__main__':
    subprocess.Popen(
        ['mitmdump', '-qs', 'sniffer.py'], text=True, encoding='UTF-8')
    time.sleep(10.0)

    options = Options()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--proxy-server=http://localhost:8080')
    options.add_argument('--ignore-certificate-errors')

    with Chrome(options=options) as driver:
        main(driver)
