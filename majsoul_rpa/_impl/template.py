#!/usr/bin/env python3

import re
import datetime
from pathlib import Path
from typing import (Union, Tuple, Iterable,)
import yaml
import numpy
import PIL.Image
from PIL.Image import Image
import cv2
from majsoul_rpa.common import TimeoutType
from majsoul_rpa._impl.browser import BrowserBase


def pil2opencv(image: Image) -> numpy.ndarray:
    if image.getbands() == ('R', 'G', 'B'):
        image = numpy.array(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    elif image.getbands() == ('R', 'G', 'B', 'A'):
        image = numpy.array(image)
        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    else:
        raise RuntimeError(f'{image.getbands()}: An unknown bands.')
    return image


class Template(object):
    def __init__(
        self, path: Path, *, left: int=0, top: int=0, width: int=1920,
        height: int=1080, threshold: float=0.99) -> None:
        self.__path = path
        self.__left = left
        self.__top = top
        self.__width = width
        self.__height = height
        self.__threshold = threshold

    @staticmethod
    def open(name_or_path: Union[str, Path]) -> 'Template':
        if isinstance(name_or_path, str):
            if not Path(f'{name_or_path}.yaml').exists():
                if Path(f'{name_or_path}.png').exists():
                    return Template(Path(f'{name_or_path}.png'))
                if name_or_path.endswith('.png'):
                    return Template(Path(f'{name_or_path}'))
                if not name_or_path.endswith('.yaml'):
                    raise ValueError(f'{name_or_path}: an invalid template.')
                path = Path(name_or_path)
            else:
                path = Path(f'{name_or_path}.yaml')
        else:
            path = name_or_path
        if not path.exists():
            raise ValueError(f'{path}: does not exist.')
        if str(path).endswith('.png'):
            return Template(path)

        with open(path) as f:
            config = yaml.load(f, Loader=yaml.Loader)

        if 'path' in config:
            png_path: str = config['path']
            if png_path.startswith('./'):
                png_path = path.parent / png_path
            else:
                png_path = Path(png_path)
            del config['path']
        else:
            png_path = Path(re.sub('\\.yaml$', '.png', str(path)))
        if not png_path.exists():
            raise RuntimeError(f'{png_path}: does not exist.')

        return Template(png_path, **config)

    def best_template_match(self, screenshot: Image) -> Tuple[int, int, float]:
        box = (
            self.__left, self.__top,
            self.__left + self.__width, self.__top + self.__height)
        image = screenshot.crop(box=box)
        image = pil2opencv(image)

        template = PIL.Image.open(self.__path)
        template = pil2opencv(template)

        if template.shape[0] == 0:
            raise ValueError('The height of the template is equal to 0.')
        if image.shape[0] < template.shape[0]:
            raise ValueError(
                f"The height of the screenshot ({image.shape[0]}) is smaller"
                f"than the template's ({template.shape[0]}).")
        if template.shape[1] == 0:
            raise ValueError('The width of the template is equal to 0.')
        if image.shape[1] < template.shape[1]:
            raise ValueError(
                f"The width of the screenshot ({image.shape[1]}) is smaller"
                f" than the template's ({template.shape[1]}).")

        result1: numpy.ndarray = cv2.matchTemplate(
            image, template, cv2.TM_CCOEFF_NORMED)
        result2: numpy.ndarray = cv2.matchTemplate(
            image, template, cv2.TM_SQDIFF_NORMED)

        argmax_x = 0
        argmax_y = 0
        max_score = result1[0, 0]
        for x in range(result1.shape[1]):
            for y in range(result1.shape[0]):
                score = max(result1[y, x], 1.0 - result2[y, x])
                if score > max_score:
                    argmax_x = x
                    argmax_y = y
                    max_score = score

        return (self.__left + argmax_x, self.__top + argmax_y, max_score)

    def match(self, screenshot: Image) -> bool:
        x, y, score = self.best_template_match(screenshot)
        return score >= self.__threshold

    def wait_until(
        self, browser: BrowserBase, deadline: datetime.datetime) -> None:
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                from majsoul_rpa.presentation import Timeout
                raise Timeout('Timeout', browser.get_screenshot())
            if self.match(browser.get_screenshot()):
                break

    def wait_for(self, browser: BrowserBase, timeout: TimeoutType) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)

        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout
        self.wait_until(browser, deadline)

    def click(self, browser: BrowserBase, edge_sigma: float=0.2) -> None:
        x, y, score = self.best_template_match(browser.get_screenshot())
        with PIL.Image.open(self.__path) as image:
            browser.click_region(x, y, image.width, image.height, edge_sigma)

    def wait_until_then_click(
        self, browser: BrowserBase, deadline: datetime.datetime,
        edge_sigma: float=0.2) -> None:
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                from majsoul_rpa.presentation import Timeout
                raise Timeout('Timeout', browser.get_screenshot())
            x, y, score = self.best_template_match(browser.get_screenshot())
            if score >= self.__threshold:
                break

        with PIL.Image.open(self.__path) as image:
            browser.click_region(x, y, image.width, image.height, edge_sigma)

    def wait_for_then_click(
        self, rpa_or_browser, timeout: TimeoutType,
        edge_sigma: float=0.2) -> None:
        from majsoul_rpa import RPA
        if isinstance(rpa_or_browser, RPA):
            browser = rpa_or_browser._get_browser()
        else:
            browser: BrowserBase = rpa_or_browser
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        self.wait_until_then_click(
            browser, datetime.datetime.now(datetime.timezone.utc) + timeout,
            edge_sigma)

    @staticmethod
    def match_one_of(screenshot: Image, templates: Iterable[Image]) -> int:
        for i in range(len(templates)):
            template = Template.open(templates[i])
            if template.match(screenshot):
                return i
        return -1

    @staticmethod
    def wait_until_one_of_then_click(
        templates: Iterable['Template'], browser: BrowserBase,
        deadline: datetime.datetime, edge_sigma: float=0.2) -> None:
        while True:
            if datetime.datetime.now(datetime.timezone.utc) > deadline:
                from majsoul_rpa.presentation import Timeout
                raise Timeout('Timeout', browser.get_screenshot())

            screenshot = browser.get_screenshot()
            match = False
            for template in templates:
                x, y, score = template.best_template_match(screenshot)
                if score >= template.__threshold:
                    with PIL.Image.open(template.__path) as image:
                        browser.click_region(
                            x, y, image.width, image.height, edge_sigma)
                    return

    @staticmethod
    def wait_for_one_of_then_click(
        templates: Iterable['Template'], browser: BrowserBase,
        timeout: TimeoutType, edge_sigma: float=0.2) -> None:
        if isinstance(timeout, (int, float,)):
            timeout = datetime.timedelta(seconds=timeout)
        deadline = datetime.datetime.now(datetime.timezone.utc) + timeout
        Template.wait_until_one_of_then_click(
            templates, browser, deadline, edge_sigma)
