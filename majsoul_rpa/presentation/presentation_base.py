#!/usr/bin/env python3

from typing import (Optional,)
from PIL.Image import Image
from majsoul_rpa._impl import Redis


class ErrorBase(Exception):
    def __init__(self, message: str, screenshot: Optional[Image]) -> None:
        self.__message = message
        self.__screenshot = screenshot


class Timeout(ErrorBase):
    def __init__(self, message: str, screenshot: Image) -> None:
        super(Timeout, self).__init__(message, screenshot)


class PresentationNotDetected(ErrorBase):
    def __init__(self, message: str, screenshot: Image) -> None:
        super(PresentationNotDetected, self).__init__(message, screenshot)


class StalePresentation(ErrorBase):
    def __init__(self, message: str, screenshot: Image) -> None:
        super(StalePresentation, self).__init__(message, screenshot)


class PresentationNotUpdated(ErrorBase):
    def __init__(self, message: str, screenshot: Optional[Image]) -> None:
        super(PresentationNotUpdated, self).__init__(message, screenshot)


class InconsistentMessage(ErrorBase):
    def __init__(self, message: str, screenshot: Optional[Image]=None) -> None:
        super(InconsistentMessage, self).__init__(message, screenshot)


class InvalidOperation(ErrorBase):
    def __init__(self, message: str, screenshot: Image) -> None:
        super(InvalidOperation, self).__init__(message, screenshot)


class RebootRequest(ErrorBase):
    def __init__(self, message: str, screenshot: Optional[Image]=None) -> None:
        super(RebootRequest, self).__init__(message, screenshot)


class PresentationBase(object):
    def __init__(self, redis: Optional[Redis]) -> None:
        self.__redis = redis
        self.__new_presentation = None

    def _set_new_presentation(
        self, new_presentation: 'PresentationBase') -> None:
        if self.__new_presentation is not None:
            raise RuntimeError('A new presentation has been already set.')
        self.__new_presentation = new_presentation

    def _get_redis(self) -> Redis:
        return self.__redis

    def _assert_not_stale(self) -> None:
        if self.__new_presentation is not None:
            raise AssertionError('The presentation has been already stale.')

    @property
    def new_presentation(self) -> Optional['PresentationBase']:
        return self.__new_presentation
