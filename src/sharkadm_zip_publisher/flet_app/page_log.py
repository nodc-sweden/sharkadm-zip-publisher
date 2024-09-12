import flet as ft


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
