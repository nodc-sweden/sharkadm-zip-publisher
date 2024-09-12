from sharkadm import utils
import pathlib


USER_DIR = utils.get_root_directory() / 'zip_archive_publisher'
USER_DIR.mkdir(parents=True, exist_ok=True)
SAVES_PATH = pathlib.Path(USER_DIR, 'zip_archive_publisher_saves.yaml').resolve()


def fix_url_str(url: str) -> str:
    prefix = 'https://'
    url = url.strip().replace('\\', '/').strip('/')
    if not url:
        return ''
    if not url.startswith(prefix):
        url = prefix + url
    return url
