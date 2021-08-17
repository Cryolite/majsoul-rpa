#!/usr/bin/env python3

import datetime
from typing import Iterable
from PIL.Image import Image
from majsoul_rpa._impl import (Template, Redis)
from majsoul_rpa.common import (Player,)
from majsoul_rpa.presentation.presentation_base import (
    InconsistentMessage, PresentationNotDetected, PresentationNotUpdated,
    InvalidOperation, PresentationBase)


class RoomPlayer(Player):
    def __init__(
        self, account_id: int, name: str, is_host: bool,
        is_ready: bool) -> None:
        super(RoomPlayer, self).__init__(account_id, name)
        self.__is_host = is_host
        self.__is_ready = is_ready

    @property
    def is_host(self) -> bool:
        return self.__is_host

    @property
    def is_ready(self) -> bool:
        return self.__is_ready

    def _set_ready(self, is_ready: bool) -> None:
        self.__is_ready = is_ready


class RoomPresentationBase(PresentationBase):
    def __init__(
        self, screenshot: Image, redis: Redis, room_id: int,
        max_num_players: int, players: Iterable[RoomPlayer], num_cpus: int,
        timestamp: datetime.datetime) -> None:
        super(RoomPresentationBase, self).__init__(screenshot, redis)

        self.__room_id = room_id
        self.__max_num_players = max_num_players
        self.__players = [p for p in players]
        self._num_cpus = num_cpus
        self._timestamp = timestamp

    def _update(self, timeout: float) -> bool:
        self._assert_not_stale()

        message = self._redis.dequeue_message(timeout)
        if message is None:
            return False

        direction, name, request, response, timestamp = message
        if name == '.lq.NotifyRoomPlayerUpdate':
            if direction != 'inbound':
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerUpdate` is not inbound.',
                    self.screenshot)
            if response is not None:
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerUpdate` has a response.',
                    self.screenshot)
            host_account_id = request['owner_id']
            new_players = []
            for p in request['player_list']:
                account_id = p['account_id']
                player = RoomPlayer(
                    account_id, p['nickname'], account_id == host_account_id,
                    False)
            self.__players = new_players
            self._num_cpus = request['robot_count']
            self._timestamp = timestamp

            return True
        elif name == '.lq.NotifyRoomPlayerReady':
            if direction != 'inbound':
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerReady` is not inbound.',
                    self.screenshot)
            if response is not None:
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerReady` has a response.',
                    self.screenshot)
            account_id = request['account_id']
            for i in range(len(self.__players)):
                self.__players[i].account_id == account_id
                break
            if i == len(self.__players):
                raise InconsistentMessage(
                    'An inconsistent `.lq.NotifyRoomPlayerReady` message.',
                    self.screenshot)
            self.__players[i]._set_ready(request['ready'])
            self._timestamp = timestamp

            return True

    @property
    def room_id(self):
        return self.__room_id

    @property
    def max_num_players(self) -> int:
        return self.__max_num_players

    @property
    def players(self) -> Iterable[RoomPlayer]:
        return self.__players

    @property
    def num_cpus(self) -> int:
        return self._num_cpus

    @property
    def timestamp(self) -> datetime.datetime:
        self._timestamp

    def leave(self, rpa, timeout: float=10.0):
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        # 部屋を出るためのアイコンをクリックする．
        template = Template.open('template/room/leave')
        if not template.match(rpa.get_screenshot()):
            raise InvalidOperation(
                'Could not leave the room.', rpa.get_screenshot())
        template.click(rpa._get_browser())

        from majsoul_rpa.presentation import HomePresentation

        # ホーム画面が表示されるまで待つ．
        HomePresentation._wait(rpa._get_browser(), timeout)

        p = HomePresentation._create(rpa.get_screenshot(), rpa._get_redis())
        self._become_stale()
        return p
