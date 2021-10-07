#!/usr/bin/env python3

import datetime
from typing import Optional
from majsoul_rpa.presentation.presentation_base import InconsistentMessage
from majsoul_rpa.presentation.match.event._base import EventBase


class LiujuEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(LiujuEvent, self).__init__(timestamp)

        if data['type'] not in (1, 4):
            raise NotImplementedError(data['type'])
        self.__type = (None, '九種九牌', None, None, '四家立直')[data['type']]
        if self.__type == '九種九牌':
            self.__seat = data['seat']
        else:
            if data['seat'] != 0:
                raise InconsistentMessage(
                    f'type = {data["type"]}, seat = {data["seat"]}')
            self.__seat = None

    @property
    def type_(self) -> str:
        return self.__type

    @property
    def seat(self) -> Optional[int]:
        return self.__seat
