import flet as ft


class ZipPath(ft.UserControl):
    def __init__(self, path: str, on_delete=None):
        super().__init__()
        self.path = str(path)
        self._on_delete = on_delete

    def build(self):
        return ft.Row([
            ft.IconButton(
                ft.icons.DELETE_OUTLINE,
                tooltip="Ta bort",
                on_click=self._delete,
            ),
            ft.Text(self.path),

        ])

    def _delete(self, e):
        self._on_delete(self)
