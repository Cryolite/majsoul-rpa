#!/usr/bin/env python3

import datetime
from majsoul_rpa.presentation.match.event._base import EventBase


class NoTileEvent(EventBase):
    def __init__(self, data: object, timestamp: datetime.datetime) -> None:
        super(NoTileEvent, self).__init__(timestamp)
        # TODO:
