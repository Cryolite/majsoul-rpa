#!/usr/bin/env python3

import datetime
from typing import Optional
from majsoul_rpa.presentation.match.event._base import EventBase


class ZimoEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(ZimoEvent, self).__init__(timestamp)
        self.__seat = data['seat']
        if data['tile'] != '':
            self.__tile = data['tile']
        else:
            self.__tile = None
        self.__left_tile_count = data['left_tile_count']

    @property
    def seat(self) -> int:
        assert(self.__seat >= 0)
        assert(self.__seat < 4)
        return self.__seat

    @property
    def tile(self) -> Optional[str]:
        return self.__tile

    @property
    def left_tile_count(self) -> int:
        assert(self.__left_tile_count < 70)
        assert(self.__left_tile_count >= 0)
        return self.__left_tile_count
