#!/usr/bin/env python3

import datetime
import PIL.Image
from majsoul_rpa._impl import Template
from majsoul_rpa.presentation.presentation_base \
    import (Timeout, PresentationNotDetected, PresentationBase,)


class LoginPresentation(PresentationBase):
    def __init__(self, screenshot: PIL.Image.Image) -> None:
        super(LoginPresentation, self).__init__(screenshot, None)

        template = Template.open('template/login/marker')
        if not template.match(screenshot):
            raise PresentationNotDetected(
                'Could not detect `LoginPresentation`.', self.screenshot)

    def login(self, rpa, timeout: float=60.0):
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        template = Template.open('template/login/marker')
        template.click(rpa._get_browser())

        start_time = datetime.datetime.now(datetime.timezone.utc)
        while True:
            now = datetime.datetime.now(datetime.timezone.utc)
            if now - start_time > datetime.timedelta(seconds=timeout):
                raise Timeout(
                    'Timeout in transition from `login`.', rpa.get_screenshot())

            screenshot = rpa.get_screenshot()

            try:
                from majsoul_rpa.presentation import AuthPresentation
                p = AuthPresentation(screenshot)
                self._become_stale()
                return p
            except PresentationNotDetected as e:
                pass

            try:
                from majsoul_rpa.presentation import HomePresentation
                p = HomePresentation._create(screenshot, rpa._get_redis())
                self._become_stale()
                return p
            except PresentationNotDetected as e:
                pass
