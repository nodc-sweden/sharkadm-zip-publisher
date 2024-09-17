import pathlib


def get_zip_name_without_date(zip_name: str) -> str:
    return zip_name.split('_version_')[0]


def get_zip_name_path_mapping(directory: str | pathlib.Path) -> dict[str, pathlib.Path]:
    mapped = dict()
    for path in pathlib.Path(directory).iterdir():
        if path.suffix != '.zip':
            continue
        mapped[get_zip_name_without_date(path.stem)] = path
    return mapped