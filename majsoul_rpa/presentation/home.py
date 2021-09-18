#!/usr/bin/env python3

import datetime
import time
from PIL.Image import Image
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl import (BrowserBase, Template, Redis)
from majsoul_rpa.presentation.presentation_base import PresentationBase
from majsoul_rpa.presentation import (Timeout, PresentationNotDetected)


class HomePresentation(PresentationBase):
    @staticmethod
    def __match_markers(screenshot: Image):
        for i in range(1, 4):
            template = Template.open(f'template/home/marker{i}')
            if not template.match(screenshot):
                return False
        return True

    @staticmethod
    def _wait(browser: BrowserBase, timeout: TimeoutType) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        now = datetime.datetime.now(datetime.timezone.utc)
        template = Template.open(f'template/home/marker0')
        template.wait_for(browser, deadline - now)

        if not HomePresentation.__match_markers(browser.get_screenshot()):
            # ホーム画面に告知が表示されている場合それらを閉じる．
            template0 = Template.open('template/home/notification_close')
            template1 = Template.open('template/home/event_close')
            while True:
                if datetime.datetime.now(datetime.timezone.utc) > deadline:
                    raise Timeout('Timeout.', browser.get_screenshot())

                screenshot = browser.get_screenshot()

                x, y, score = template0.best_template_match(screenshot)
                if score >= 0.99:
                    browser.click_region(x, y, 30, 30)
                    time.sleep(1.0)
                    continue

                x, y, score = template1.best_template_match(screenshot)
                if score >= 0.99:
                    browser.click_region(x, y, 71, 71)
                    time.sleep(1.0)
                    continue

                break

            while True:
                if datetime.datetime.now(datetime.timezone.utc) > deadline:
                    raise Timeout('Timeout.', browser.get_screenshot())
                if HomePresentation.__match_markers(browser.get_screenshot()):
                    break

    def __init__(self, screenshot: Image, redis: Redis) -> None:
        super(HomePresentation, self).__init__(redis)

        if not HomePresentation.__match_markers(screenshot):
            raise PresentationNotDetected(
                'Could not detect `home`.', screenshot)

        while self._get_redis().dequeue_message() is not None:
            pass

    def create_room(self, rpa, timeout: TimeoutType=60.0) -> None:
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        # 「友人戦」をクリックする．
        rpa._click_template('template/home/marker3')

        # 「ルーム作成」が表示されるまで待つ．
        template = Template.open('template/home/room_creation')
        template.wait_until(rpa._get_browser(), deadline)

        # 「ルーム作成」をクリックする．
        rpa._click_template('template/home/room_creation')

        # 「作成」が表示されるまで待つ．
        template = Template.open('template/home/room_creation/confirm')
        template.wait_until(rpa._get_browser(), deadline)

        # 「作成」をクリックする．
        rpa._click_template('template/home/room_creation/confirm')

        from majsoul_rpa.presentation import RoomHostPresentation

        # 部屋の画面が表示されるまで待つ．
        now = datetime.datetime.now(datetime.timezone.utc)
        RoomHostPresentation._wait(rpa._get_browser(), deadline - now)

        p = RoomHostPresentation._create(rpa.get_screenshot(), rpa._get_redis())
        self._set_new_presentation(p)
