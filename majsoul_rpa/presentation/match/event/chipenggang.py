#!/usr/bin/env python3

import datetime
from typing import List
from majsoul_rpa.presentation.match.event._base import EventBase


class ChiPengGangEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime) -> None:
        super(ChiPengGangEvent, self).__init__(timestamp)
        self.__seat = data['seat']
        self.__type = ('チー', 'ポン', '大明槓')[data['type']]
        self.__from = data['froms'][-1]
        self.__tiles = data['tiles']

    @property
    def seat(self) -> int:
        assert(self.__seat >= 0)
        assert(self.__seat < 4)
        return self.__seat

    @property
    def type_(self) -> str:
        return self.__type

    @property
    def from_(self) -> int:
        return self.__from

    @property
    def tiles(self) -> List[str]:
        return self.__tiles
