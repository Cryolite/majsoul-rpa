#!/usr/bin/env python3

from typing import (List, Iterable)
from PIL.Image import Image
from majsoul_rpa.common import (Player, TimeoutType,)
from majsoul_rpa._impl import (Template, Redis,)
from majsoul_rpa.presentation.presentation_base import (
    InconsistentMessage, InvalidOperation, PresentationBase,)


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
        self, redis: Redis, room_id: int,
        max_num_players: int, players: Iterable[RoomPlayer],
        num_cpus: int) -> None:
        super(RoomPresentationBase, self).__init__(redis)

        self.__room_id = room_id
        self.__max_num_players = max_num_players
        self.__players = [p for p in players]
        self._num_cpus = num_cpus

    def _update(self, timeout: TimeoutType) -> bool:
        self._assert_not_stale()

        message = self._get_redis().dequeue_message(timeout)
        if message is None:
            return False
        direction, name, request, response, timestamp = message

        if name == '.lq.Lobby.modifyRoom':
            return False

        if name == '.lq.NotifyRoomPlayerUpdate':
            if direction != 'inbound':
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerUpdate` is not inbound.', None)
            if response is not None:
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerUpdate` has a response.', None)
            host_account_id = request['owner_id']
            new_players = []
            for p in request['player_list']:
                account_id = p['account_id']
                player = RoomPlayer(
                    account_id, p['nickname'], account_id == host_account_id,
                    False)
            self.__players = new_players
            self._num_cpus = request['robot_count']

            return True

        if name == '.lq.NotifyRoomPlayerReady':
            if direction != 'inbound':
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerReady` is not inbound.', None)
            if response is not None:
                raise InconsistentMessage(
                    '`.lq.NotifyRoomPlayerReady` has a response.', None)
            account_id = request['account_id']
            for i in range(len(self.__players)):
                self.__players[i].account_id == account_id
                break
            if i == len(self.__players):
                raise InconsistentMessage(
                    'An inconsistent `.lq.NotifyRoomPlayerReady` message.',
                    None)
            self.__players[i]._set_ready(request['ready'])

            return True

        raise InconsistentMessage(f'''An inconsistent message.
direction: {direction}
name: {name}
request: {request}
response: {response}
timestamp: {timestamp}''', None)

    @property
    def room_id(self) -> int:
        return self.__room_id

    @property
    def max_num_players(self) -> int:
        return self.__max_num_players

    @property
    def players(self) -> List[RoomPlayer]:
        return self.__players

    @property
    def num_cpus(self) -> int:
        return self._num_cpus

    def leave(self, rpa, timeout: TimeoutType=10.0) -> None:
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

        p = HomePresentation(rpa.get_screenshot(), rpa._get_redis())
        self._set_new_presentation(p)
