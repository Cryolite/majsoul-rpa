#!/usr/bin/env python3

import datetime
import time
from typing import (List, Iterable)
from PIL.Image import Image
from majsoul_rpa._impl import (Template, BrowserBase, Message, Redis)
from majsoul_rpa.presentation.presentation_base import (
    PresentationNotDetected, InconsistentMessage, InvalidOperation,
    PresentationNotUpdated)
from majsoul_rpa.presentation.room.base import (
    RoomPlayer, RoomPresentationBase)


class RoomHostPresentation(RoomPresentationBase):
    @staticmethod
    def _wait(browser: BrowserBase, timeout: float=60.0) -> None:
        template = Template.open('template/room/marker')
        template.wait_for(browser, timeout)

    def __init__(
        self, screenshot: Image, redis: Redis, room_id: int,
        max_num_players: int, players: Iterable[RoomPlayer], num_cpus: int,
        timestamp: datetime.datetime):
        super(RoomHostPresentation, self).__init__(
            screenshot, redis, room_id, max_num_players, players, num_cpus,
            timestamp)

    @staticmethod
    def create(screenshot: Image, redis: Redis) -> 'RoomHostPresentation':
        template = Template.open('template/room/marker')
        if not template.match(screenshot):
            raise PresentationNotDetected(
                'Could not detect `room`.', screenshot)

        while True:
            message = redis.dequeue_message()
            if message is None:
                raise InconsistentMessage(
                    '`.lq.Lobby.createRoom` not found.', screenshot)
            direction, name, request, response, timestamp = message
            if name == '.lq.Lobby.createRoom':
                break

        if direction != 'outbound':
            raise InconsistentMessage(
                '`.lq.Lobby.createRoom` is not outbound.', screenshot)
        # TODO: ルール詳細の記録
        if response is None:
            raise InconsistentMessage(
                '`.lq.Lobby.createRoom` does not have any response.',
                screenshot)

        room = response['room']
        room_id: int = room['room_id']
        max_num_players: int = room['max_player_count']
        if len(room['persons']) != 1:
            raise InconsistentMessage(
                'An inconsistent `.lq.Lobby.createRoom` message.', screenshot)
        host = room['persons'][0]
        player = RoomPlayer(host['account_id'], host['nickname'], True, True)
        players = []
        players.append(player)

        return RoomHostPresentation(
            screenshot, redis, room_id, max_num_players, players, 0, timestamp)

    def _deep_copy(self) -> 'RoomHostPresentation':
        return RoomHostPresentation(
            self.screenshot, self._redis, self.room_id, self.max_num_players,
            self.players, self.num_cpus, self.timestamp)

    def _update(self, timeout: float) -> 'RoomHostPresentation':
        self._assert_not_stale()

        new_presentation = self._deep_copy()
        if not super(RoomHostPresentation, new_presentation)._update(timeout):
            raise PresentationNotUpdated(
                '`room_host` has not been updated.', self.screenshot)

        self._become_stale()
        return new_presentation

    def add_cpu(self, rpa, timeout: float=10.0) -> 'RoomHostPresentation':
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        start_time = datetime.datetime.now(datetime.timezone.utc)
        deadline = start_time + datetime.timedelta(seconds=timeout)

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
        p = self
        while p.num_cpus <= old_num_cpus:
            now = datetime.datetime.now(datetime.timezone.utc)
            timeout = (deadline - now).microseconds / 1000000.0
            try:
                p = p._update(timeout)
            except PresentationNotUpdated as e:
                pass

        if self is not p:
            self._become_stale()
        return p
