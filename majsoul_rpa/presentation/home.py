#!/usr/bin/env python3

import datetime
from PIL.Image import Image
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
    def _wait(browser: BrowserBase, timeout: float=60.0) -> None:
        template = Template.open(f'template/home/marker0')
        template.wait_for(browser, timeout)

        if not HomePresentation.__match_markers(browser.get_screenshot()):
            # ホーム画面に告知が表示されている場合それらを閉じる．
            template = Template.open('template/home/notification_close')
            start_time = datetime.datetime.now(datetime.timezone.utc)
            while True:
                x, y, score = template.best_template_match(
                    browser.get_screenshot())
                if score >= 0.99:
                    browser.click_region(x, y, 30, 30)
                    continue
                break

            start_time = datetime.datetime.now(datetime.timezone.utc)
            while True:
                now = datetime.datetime.now(datetime.timezone.utc)
                if now - start_time > datetime.timedelta(seconds=timeout):
                    raise Timeout(
                        'Timeout in detecting `home`.',
                        browser.get_screenshot())
                if HomePresentation.__match_markers(browser.get_screenshot()):
                    break

    def __init__(self, screenshot: Image, redis: Redis) -> None:
        super(HomePresentation, self).__init__(screenshot, redis)

        if not HomePresentation.__match_markers(screenshot):
            raise PresentationNotDetected(
                'Could not detect `home`.', screenshot)

        while self._redis.dequeue_message() is not None:
            pass

    @staticmethod
    def _create(screenshot: Image, redis: Redis) -> 'HomePresentation':
        return HomePresentation(screenshot, redis)

    def create_room(self, rpa, timeout: float=60.0):
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        start_time = datetime.datetime.now(datetime.timezone.utc)
        deadline = start_time + datetime.timedelta(seconds=timeout)

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
        RoomHostPresentation._wait(
            rpa._get_browser(), (deadline - now).microseconds / 1000000.0)

        p = RoomHostPresentation.create(rpa.get_screenshot(), rpa._get_redis())
        self._become_stale()
        return p
