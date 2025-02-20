import flet as ft

from sharkadm_zip_publisher.archive_publisher import ArchivePublisher
from sharkadm_zip_publisher.flet_app import utils
from sharkadm import utils as sharkadm_utils


class PageTransformers(ft.UserControl):

    def __init__(self, main_app):
        super().__init__()
        self.main_app = main_app

    def build(self):
        self.lv = ft.ListView(expand=1, spacing=10, padding=20, auto_scroll=True)
        self.expand = True
        col = ft.Column([
            ft.Text(
                'Transformationer som kommer utföras vid arkivering:',
                size=40,
                # color=ft.colors.WHITE,
                # bgcolor=ft.colors.BLUE_600,
                weight=ft.FontWeight.W_100,
            ),
            ft.Divider(),
            self.lv
        ], expand=True)
        self._set_transformers_column()

        return col

    def _set_transformers_column(self) -> None:
        pub = ArchivePublisher()
        info = pub.all_transformers
        self.lv.controls.append(ft.Text('Utförs alltid', weight=ft.FontWeight('bold')))
        for tran in info['mandatory']:
            self.lv.controls.append(ft.Row([ft.Text(tran.description),
                                            ft.Text(f'({tran.__class__.__name__})')],
                                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        self.lv.controls.append(ft.Divider())
        self.lv.controls.append(ft.Text('Utförs om begränsad åtkomst är vald', weight=ft.FontWeight('bold')))
        for tran in info['restricted']:
            self.lv.controls.append(ft.Row([ft.Text(tran.description),
                                            ft.Text(f'({tran.__class__.__name__})')],
                                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
