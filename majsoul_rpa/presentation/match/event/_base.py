#!/usr/bin/env python3

import datetime


class EventBase(object):
    def __init__(self, timestamp: datetime.datetime) -> None:
        self.__timestamp = timestamp

    @property
    def timestamp(self) -> datetime.datetime:
        return self.__timestamp
