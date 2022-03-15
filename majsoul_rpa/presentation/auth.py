#!/usr/bin/env python3

import datetime
import time
from PIL.Image import Image
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl import (Template, BrowserBase,)
from majsoul_rpa.presentation.presentation_base \
    import (InvalidOperation, PresentationNotDetected, PresentationBase)


class AuthPresentation(PresentationBase):
    @staticmethod
    def _wait(browser: BrowserBase, timeout: TimeoutType=10.0) -> None:
        template = Template.open('template/auth/marker')
        template.wait_for(browser, timeout)

    def __init__(self, screenshot: Image) -> None:
        super(AuthPresentation, self).__init__(redis=None)

        self.__mail_address = None

        template = Template.open('template/auth/marker')
        if not template.match(screenshot):
            raise PresentationNotDetected(
                'Could not detect `LoginPresentation`.', screenshot)

    def get_mail_address(self) -> str:
        if self.__mail_address is None:
            raise ValueError('Mail address has not been entered yet.')
        return self.__mail_address

    def enter_mail_address(
        self, rpa, mail_address: str, timeout: TimeoutType=10.0) -> None:
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if self.__mail_address is not None:
            raise InvalidOperation(
                'Mail address has been already entered.', rpa.get_screenshot())

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        # 「メールアドレス」のテキストボックスをクリックしてフォーカスする．
        rpa._click_region(480, 373, 428, 55)

        # テキストボックスにメールアドレスを入力する．
        rpa._press_hotkey('ctrl', 'a')
        rpa._press('backspace')
        rpa._write(mail_address)
        self.__mail_address = mail_address

        # 「コードを受け取る」ボタンをクリックする．
        rpa._click_region(843, 495, 206, 85)

        # ダイアログボックスが表示されるのを待つ．
        template = Template.open('template/auth/confirm')
        template.wait_for(rpa._get_browser(), timeout)

        # 「確認」ボタンをクリックする．
        template.click(rpa._get_browser())
        time.sleep(0.1)

    def enter_auth_code(
        self, rpa, auth_code: str, timeout: TimeoutType=120.0) -> None:
        self._assert_not_stale()

        from majsoul_rpa import RPA
        rpa: RPA = rpa

        if self.__mail_address is None:
            raise InvalidOperation(
                'Mail address has not been entered yet.', rpa.get_screenshot())

        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout

        # 「認証コード」のテキストボックスをクリックしてフォーカス
        rpa._click_region(433, 510, 288, 55)

        # テキストボックスに認証コードを入力
        rpa._press_hotkey('ctrl', 'a')
        rpa._press('backspace')
        rpa._write(auth_code)

        # 「ログイン」ボタンが有効化されるのを待つ
        template = Template.open('template/auth/login')
        template.wait_until(rpa._get_browser(), deadline)

        # 「ログイン」ボタンをクリック
        template.click(rpa._get_browser())

        from majsoul_rpa.presentation import HomePresentation

        # ホーム画面が表示されるまで待つ．
        timeout = deadline - datetime.datetime.now(datetime.timezone.utc)
        HomePresentation._wait(rpa._get_browser(), timeout)

        p = HomePresentation(rpa.get_screenshot(), rpa._get_redis(), 60.0)
        self._set_new_presentation(p)
