#!/usr/bin/env python3

import datetime
from majsoul_rpa.presentation.match.event._base import EventBase


class DapaiEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(DapaiEvent, self).__init__(timestamp)
        self.__seat = data['seat']
        self.__tile = data['tile']
        self.__moqie = data['moqie']
        self.__liqi = data['is_liqi']
        self.__wliqi = data['is_wliqi']

    @property
    def seat(self) -> int:
        assert(self.__seat >= 0)
        assert(self.__seat < 4)
        return self.__seat

    @property
    def tile(self) -> str:
        return self.__tile

    @property
    def moqie(self) -> bool:
        return self.__moqie

    @property
    def liqi(self) -> bool:
        return self.__liqi

    @property
    def wliqi(self) -> bool:
        return self.__wliqi
