#!/usr/bin/env python3

import datetime
import time
import logging
from typing import (List, Iterable)
from PIL.Image import Image
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl import (Template, BrowserBase, Redis)
from majsoul_rpa.presentation.presentation_base import (
    Timeout, PresentationNotDetected, InconsistentMessage, InvalidOperation,
    PresentationNotUpdated)
from majsoul_rpa.presentation.room.base import (
    RoomPlayer, RoomPresentationBase)


class RoomHostPresentation(RoomPresentationBase):
    @staticmethod
    def _wait(browser: BrowserBase, timeout: TimeoutType=60.0) -> None:
        template = Template.open('template/room/marker')
        template.wait_for(browser, timeout)

    def __init__(
        self, screenshot: Image, redis: Redis, room_id: int,
        max_num_players: int, players: Iterable[RoomPlayer], num_cpus: int):
        super(RoomHostPresentation, self).__init__(
            redis, room_id, max_num_players, players, num_cpus)

    @staticmethod
    def _create(
        screenshot: Image, redis: Redis,
        timeout: TimeoutType) -> 'RoomHostPresentation':
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        template = Template.open('template/room/marker')
        if not template.match(screenshot):
            raise PresentationNotDetected(
                'Could not detect `room`.', screenshot)

        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            message = redis.dequeue_message(deadline - now)
            if message is None:
                raise Timeout('Timeout.', screenshot)
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.createRoom':
                logging.info(message)
                break

            if name == '.lq.Lobby.fetchRoom':
                logging.info(message)
                break

            raise InconsistentMessage(message, screenshot)

        room: dict = response['room']
        room_id: int = room['room_id']
        owner_id: int = room['owner_id']
        if owner_id != redis.account_id:
            raise InconsistentMessage(message, screenshot)
        max_num_players: int = room['max_player_count']
        ready_list: List[int] = room['ready_list']
        players = []
        for person in room['persons']:
            account_id = person['account_id']
            player = RoomPlayer(
                account_id, person['nickname'], account_id == owner_id,
                account_id in ready_list)
        num_cpus = room['robot_count']

        return RoomHostPresentation(
            screenshot, redis, room_id, max_num_players, players, num_cpus)

    @staticmethod
    def _return_from_match(
        browser: BrowserBase, redis: Redis,
        prev_presentation: 'RoomHostPresentation',
        timeout: TimeoutType) -> 'RoomHostPresentation':
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        now = datetime.datetime.now(datetime.timezone.utc)
        RoomHostPresentation._wait(browser, deadline - now)

        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout', browser.get_screenshot())

            now = datetime.datetime.now(datetime.timezone.utc)
            message = redis.dequeue_message(deadline - now)
            if message is None:
                break
            direction, name, request, response, timestamp = message

            if name == '.lq.Lobby.heatbeat':
                continue

            if name == '.lq.FastTest.checkNetworkDelay':
                continue

            if name == '.lq.Lobby.fetchAccountInfo':
                # TODO: アカウント情報の更新
                continue

            if name == '.lq.Lobby.fetchRoom':
                # TODO: 友人戦部屋情報の更新
                continue

            raise InconsistentMessage(name, browser.get_screenshot())

        return RoomHostPresentation(
            browser.get_screenshot(), redis, prev_presentation.room_id,
            prev_presentation.max_num_players, prev_presentation.players,
            prev_presentation.num_cpus)

    def _update(self, timeout: TimeoutType) -> 'RoomHostPresentation':
        self._assert_not_stale()

        if not super(RoomHostPresentation, self)._update(timeout):
            raise PresentationNotUpdated(
                '`room_host` has not been updated yet.', None)

    def add_cpu(self, rpa, timeout: TimeoutType=10.0):
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        # 「CPU追加」がクリックできる状態か確認する．
        template = Template.open('template/room/add_cpu')
        if not template.match(rpa.get_screenshot()):
            raise InvalidOperation('Could not add CPU.', rpa.get_screenshot())

        old_num_cpus = self.num_cpus

        # 「CPU追加」をクリックする．
        template.click(rpa._get_browser())
        # 「CPU追加」をクリックした際に花びらが舞うエフェクトが発生し，
        # 連続して「CPU追加」をクリックする際にそのエフェクトが
        # テンプレートマッチングを阻害するため，エフェクトが消えるまで待つ．
        time.sleep(2.0)

        # WebSocket メッセージが飛んできて，実際に CPU の数が増えるまで待つ．
        while self.num_cpus <= old_num_cpus:
            now = datetime.datetime.now(datetime.timezone.utc)
            try:
                self._update(deadline - now)
            except PresentationNotUpdated as e:
                pass

    def start(self, rpa, timeout: TimeoutType=60.0) -> None:
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        # 「開始」アイコンが有効になるまで待った後，クリックする．
        template = Template.open('template/room/start')
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                raise Timeout('Timeout.', rpa.get_screenshot())
            if template.match(rpa.get_screenshot()):
                break
        template.click(rpa._get_browser())

        now = datetime.datetime.now(datetime.timezone.utc)
        from majsoul_rpa.presentation.match.state import MatchState
        from majsoul_rpa.presentation.match import MatchPresentation
        MatchPresentation._wait(rpa._get_browser(), deadline - now)

        now = datetime.datetime.now(datetime.timezone.utc)
        p = MatchPresentation(
            self, rpa.get_screenshot(), rpa._get_redis(), deadline - now,
            match_state=MatchState())

        self._set_new_presentation(p)
