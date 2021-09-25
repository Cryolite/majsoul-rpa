#!/usr/bin/env python3

import datetime
from typing import Optional
from majsoul_rpa.presentation.match.event._base import EventBase


class LiujuEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(LiujuEvent, self).__init__(timestamp)

        if data['type'] >= 2:
            raise NotImplementedError(data['type'])
        self.__type = (None, '九種九牌')[data['type']]
        if self.__type == '九種九牌':
            self.__seat = data['seat']
        else:
            assert(data['seat'] == '')
            self.__seat = None

    @property
    def type_(self) -> str:
        return self.__type

    @property
    def seat(self) -> Optional[int]:
        return self.__seat
