#!/usr/bin/env python3

import datetime
from typing import (Optional, Tuple, Iterable)
import PIL.Image
from majsoul_rpa._impl import Template
from majsoul_rpa.presentation.presentation_base \
    import (Timeout, PresentationBase)


class MatchPresentation(PresentationBase):
    @staticmethod
    def __match_marker(screenshot: PIL.Image.Image) -> bool:
        for i in range(4):
            template = Template.open(f'template/match/marker{i}')
            if template.match(screenshot):
                return True
        return False

    @staticmethod
    def wait(rpa, timeout: float=60.0) -> None:
        start_time = datetime.datetime.now(datetime.timezone.utc)
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            if now - start_time > datetime.timedelta(seconds=timeout):
                raise Timeout(
                    'Timeout in waiting `match`.', rpa.get_screenshot())
            if MatchPresentation.__match_marker(rpa.get_screenshot()):
                break

    def __init__(self, rpa) -> None:
        super(MatchPresentation, self).__init__(rpa)

        self.__events = []
        self.__state = None

    def _process_messages(
        self, messages: Iterable[Tuple[str, str, object, object, datetime.datetime]]):
        pass
