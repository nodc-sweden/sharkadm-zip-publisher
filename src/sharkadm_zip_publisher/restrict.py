from sharkadm import utils

CONFIG_DIR = utils.get_root_directory() / 'zip_archive_publisher' / 'config'
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

UNRESTRICTED_PACKAGES_PATH = CONFIG_DIR / 'unrestricted_packages.txt'


RESTRICT_DATA = True

DONT_REMOVE_FOLDERS_FOR_DATA_TYPES = [
    'profile'
]


DONT_PUBLISH_DATA_TYPES = [
    # 'epibenthos',
    # 'epibenthos_dropvideo',
    # 'zoobenthos',
    # 'profile'
]
UNRESTRICTED_DATA_TYPES = [
    "greyseal",
    "harbourseal",
    "ringedseal",
    "sealpathology",
]

ONLY_PUBLISH_DATA_TYPES = [
    "chlorophyll",
    "physicalchemical",
    "phytoplankton",
    "zoobenthos",
]

ONLY_PUBLISH_DATA_TYPES.extend(UNRESTRICTED_DATA_TYPES)


DEPTH_REPLACE_VALUE = '999'
COMMENT_REPLACE_VALUE = ''
SECCHI_REPLACE_VALUE = ''

DEPTH_COLUMNS = [
    'bottom_depth_m',
    'water_depth_m',
    ]

# DEPTH_COLUMNS = [
#     'bottom_depth_m',
#     'water_depth_m',
#     'sample_min_depth_m',
#     'sample_max_depth_m',
#     'transect_min_depth_m',
#     'transect_max_depth_m',
#     'transect_start_depth_m',
#     'transect_stop_depth_m',
#     'section_start_depth_m',
#     'section_end_depth_m',
#     ]

SECCHI_COLUMNS = [
    'secchi_depth_m',
    'secchi_depth_quality_flag',
    ]

REMOVE_PARAMETER_ROWS = [
    'Secchi depth',
]

COMMENT_COLUMNS = [
    'visit_comment',
    'sample_comment',
    'variable_comment',
    'sampling_method_comment_phyche',
    'section_comment',
    'transect_comment',
    'calculation_comment',
    'relative_abundance_comment',
    'sect_substrate_comment',
    'method_comment',
    'sediment_comment',

    'sample_substrate_comnt_boulder',
    'sample_substrate_comnt_rock',
    'sample_substrate_comnt_softbottom',
    'sample_substrate_comnt_stone',
    'sample_substrate_comnt_gravel',
    'sample_substrate_comnt_sand',

    'section_substrate_comnt_boulder',
    'section_substrate_comnt_gravel',
    'section_substrate_comnt_rock',
    'section_substrate_comnt_sand',
    'section_substrate_comnt_softbottom',
    'section_substrate_comnt_stone',
]


def _reset_unrestricted_packages() -> None:
    with open(UNRESTRICTED_PACKAGES_PATH, 'w') as fid:
        pass


def get_unrestricted_packages() -> list[str]:
    if not UNRESTRICTED_PACKAGES_PATH.exists():
        _reset_unrestricted_packages()
        return []
    packs = []
    with open(UNRESTRICTED_PACKAGES_PATH) as fid:
        for line in fid:
            pack = line.strip()
            if not pack:
                continue
            packs.append(pack)
    return packs
