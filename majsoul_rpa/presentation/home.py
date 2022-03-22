#!/usr/bin/env python3

import datetime
import time
import logging
from PIL.Image import Image
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl import (BrowserBase, Template, Redis)
from majsoul_rpa.presentation.presentation_base import InconsistentMessage, PresentationBase
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
    def _close_notifications(
        browser: BrowserBase, timeout: TimeoutType) -> None:
        # ホーム画面の告知が表示されている場合にそれらを閉じる．

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        template0 = Template.open('template/home/notification_close')
        template1 = Template.open('template/home/event_close')
        template2 = Template.open('template/home/visit_to_shrine')
        template3 = Template.open('template/home/visited_to_shrine')
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

            x, y, score = template2.best_template_match(screenshot)
            if score >= 0.87: # Lower bound.
                browser.click_region(x, y, 78, 36)
                while True:
                    if datetime.datetime.now(datetime.timezone.utc) > deadline:
                        raise Timeout('Timeout.', browser.get_screenshot())
                    screenshot = browser.get_screenshot()
                    xx, yy, score = template3.best_template_match(screenshot)
                    if score >= 0.97: # Upper bound.
                        browser.click_region(xx, yy, 77, 37)
                        break
                continue

            break

    @staticmethod
    def _wait(browser: BrowserBase, timeout: TimeoutType) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        now = datetime.datetime.now(datetime.timezone.utc)
        template = Template.open(f'template/home/marker0')
        template.wait_for(browser, deadline - now)

        if not HomePresentation.__match_markers(browser.get_screenshot()):
            # ホーム画面に告知が表示されている場合にそれらを閉じる．
            now = datetime.datetime.now(datetime.timezone.utc)
            HomePresentation._close_notifications(browser, deadline - now)

            while True:
                if datetime.datetime.now(datetime.timezone.utc) > deadline:
                    raise Timeout('Timeout.', browser.get_screenshot())
                if HomePresentation.__match_markers(browser.get_screenshot()):
                    break

    def __init__(
        self, screenshot: Image, redis: Redis, timeout: TimeoutType) -> None:
        super(HomePresentation, self).__init__(redis)

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        if not HomePresentation.__match_markers(screenshot):
            raise PresentationNotDetected(
                'Could not detect `home`.', screenshot)

        num_login_beats = 0
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(deadline - now)
            if message is None:
                raise Timeout('Timeout.', screenshot)
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.NotifyAccountUpdate':
                logging.info(message)
                # TODO: メッセージ内容の解析．
                continue

            if name == '.lq.Lobby.oauth2Auth':
                logging.info(message)
                continue

            if name == '.lq.Lobby.oauth2Check':
                logging.info(message)
                continue

            if name == '.lq.Lobby.oauth2Login':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchLastPrivacy':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchServerTime':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchServerSettings':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchConnectionInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchClientValue':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchFriendList':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchFriendApplyList':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchMailInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchDailyTask':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchReviveCoinInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchTitleList':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchBagInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchShopInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchActivityList':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchAccountActivityData':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchActivityBuff':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchVipReward':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchMonthTicketInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchAchievement':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchSelfGamePointRank':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchCommentSetting':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchAccountSettings':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchModNicknameTime':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchMisc':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchAnnouncement':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchRollingNotice':
                logging.info(message)
                continue

            if name == '.lq.Lobby.loginSuccess':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchCharacterInfo':
                logging.info(message)
                continue

            if name == '.lq.Lobby.fetchAllCommonViews':
                logging.info(message)
                continue

            if name == '.lq.Lobby.loginBeat':
                logging.info(message)
                num_login_beats += 1
                if num_login_beats == 2:
                    break
                continue

            if name == '.lq.Lobby.fetchCollectedGameRecordList':
                logging.info(message)
                continue

            raise InconsistentMessage(message, screenshot)

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = self._get_redis().dequeue_message(0.1)
            if message is None:
                break
            direction, name, request, response, timestamp = message

            if name == '.lq.NotifyAccountUpdate':
                logging.info(message)
                continue

            if name == '.lq.Lobby.readAnnouncement':
                logging.info(message)
                continue

            if name == '.lq.Lobby.doActivitySignIn':
                logging.info(message)
                continue

            raise InconsistentMessage(message, screenshot)

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

        now = datetime.datetime.now(datetime.timezone.utc)
        p = RoomHostPresentation._create(
            rpa.get_screenshot(), rpa._get_redis(), deadline - now)
        self._set_new_presentation(p)
