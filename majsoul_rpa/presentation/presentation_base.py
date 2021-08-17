#!/usr/bin/env python3

from typing import (Optional,)
import PIL.Image
from majsoul_rpa._impl import Redis


class ErrorBase(Exception):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        self.__message = message
        self.__screenshot = screenshot


class Timeout(ErrorBase):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        super(Timeout, self).__init__(message, screenshot)


class PresentationNotDetected(ErrorBase):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        super(PresentationNotDetected, self).__init__(message, screenshot)


class StalePresentation(ErrorBase):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        super(StalePresentation, self).__init__(message, screenshot)


class PresentationNotUpdated(ErrorBase):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        super(PresentationNotUpdated, self).__init__(message, screenshot)


class InconsistentMessage(ErrorBase):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        super(InconsistentMessage, self).__init__(message, screenshot)


class InvalidOperation(ErrorBase):
    def __init__(self, message: str, screenshot: PIL.Image.Image) -> None:
        super(InvalidOperation, self).__init__(message, screenshot)


class PresentationBase(object):
    def __init__(
        self, screenshot: PIL.Image.Image, redis: Optional[Redis]) -> None:
        self.__screenshot = screenshot
        self._redis = redis
        self.__stale = False

    @property
    def screenshot(self) -> PIL.Image.Image:
        return self.__screenshot

    def _assert_not_stale(self) -> None:
        if self.__stale:
            raise StalePresentation(
                'The presentation is stale.', self.screenshot)

    def _become_stale(self) -> None:
        self.__stale = True

    def is_stale(self) -> bool:
        return self.__stale
