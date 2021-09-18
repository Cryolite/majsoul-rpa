#!/usr/bin/env python3

import datetime
from PIL.Image import Image
from majsoul_rpa._impl import Template
from majsoul_rpa.common import TimeoutType
from majsoul_rpa.presentation.presentation_base \
    import (Timeout, PresentationNotDetected, PresentationBase,)


class LoginPresentation(PresentationBase):
    def __init__(self, screenshot: Image) -> None:
        super(LoginPresentation, self).__init__(redis=None)

        template = Template.open('template/login/marker')
        if not template.match(screenshot):
            raise PresentationNotDetected(
                'Could not detect `LoginPresentation`.', screenshot)

    def login(self, rpa, timeout: TimeoutType=60.0) -> None:
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        template = Template.open('template/login/marker')
        template.click(rpa._get_browser())

        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            if now > deadline:
                raise Timeout(
                    'Timeout in transition from `login`.', rpa.get_screenshot())

            screenshot = rpa.get_screenshot()

            try:
                from majsoul_rpa.presentation import AuthPresentation
                p = AuthPresentation(screenshot)
                self._set_new_presentation(p)
                return
            except PresentationNotDetected as e:
                pass

            try:
                from majsoul_rpa.presentation import HomePresentation
                p = HomePresentation(screenshot, rpa._get_redis())
                self._set_new_presentation(p)
                return
            except PresentationNotDetected as e:
                pass
