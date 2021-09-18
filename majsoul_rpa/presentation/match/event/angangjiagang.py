#!/usr/bin/env python3

import datetime
from majsoul_rpa.presentation.match.event._base import EventBase


class AngangJiagangEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime) -> None:
        super(AngangJiagangEvent, self).__init__(timestamp)
        self.__seat = data['seat']
        self.__type = (None, None, '暗槓', '加槓')[data['type']]
        self.__tile = data['tiles']

    @property
    def seat(self) -> int:
        assert(self.__seat >= 0)
        assert(self.__seat < 4)
        return self.__seat

    @property
    def type_(self) -> str:
        assert(self.__type in ('暗槓', '加槓'))
        return self.__type

    @property
    def tile(self) -> str:
        return self.__tile
