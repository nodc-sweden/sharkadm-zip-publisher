import time

import flet as ft
from sharkadm import utils as sharkadm_utils

from sharkadm_zip_publisher.config_publisher import ConfigPath, ConfigPublisher
from sharkadm_zip_publisher.flet_app.constants import COLOR_CONFIG_MAIN, COLOR_DATASETS_MAIN
from sharkadm_zip_publisher.flet_app.saves import publisher_saves


class PageLog(ft.UserControl):

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

    def build(self):
        self.expand = True
        self.lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
        return self.lv

    def clear_text(self) -> None:
        self.lv.controls = []
        self.lv.update()

    def add_text(self, text: str) -> None:
        self.lv.controls.append(ft.Text(text))
        self.lv.update()

    def add_empty_line(self) -> None:
        self.add_text('\n')
