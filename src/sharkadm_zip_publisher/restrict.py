from sharkadm import utils

CONFIG_DIR = utils.get_root_directory() / 'zip_archive_publisher' / 'config'
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

UNRESTRICTED_PACKAGES_PATH = CONFIG_DIR / 'unrestricted_packages.txt'  # Is not valid at the moment


RESTRICT_DATA = False

DONT_REMOVE_FOLDERS_FOR_DATA_TYPES = [
    'profile'
]


DONT_PUBLISH_DATA_TYPES = [

]
UNRESTRICTED_DATA_TYPES = [

]

ONLY_PUBLISH_DATA_TYPES = [
]

ONLY_PUBLISH_DATA_TYPES.extend(UNRESTRICTED_DATA_TYPES)


REPLACE_PARAMETER_VALUE = "999"
REPLACE_COLUMN_VALUE = "999"
REPLACE_COMMENT_VALUE = "NA"
REPLACE_SCIENTIFIC_NAME_VALUE = "NA"
REPLACE_SECCHI_VALUE = ""


DEPTH_COLUMNS = [
    'bottom_depth_m',
    'water_depth_m',
    'transect_min_depth_m',
    'transect_max_depth_m',
    'transect_start_depth_m',
    'transect_stop_depth_m',
    'section_start_depth_m',
    'section_end_depth_m',
]

# Allt utom ox
ALL_BUT_OX = [
    # 'sampled_volume_l',
    # 'flowmeter_length_m'
    'sample_min_depth_m',
    'sample_max_depth_m',
    "sample_depth_m",
    ]



# DEPTH_COLUMNS = [".*depth.*"]

# SECCHI_COLUMNS = [
#     'secchi_depth_m',
#     'secchi_depth_quality_flag',
#     ]

SECCHI_COLUMNS = [
    '.*secchi.*',
    '.*Secchi.*',
    ]
#
# REMOVE_PARAMETER_ROWS = [
#     'Secchi depth',
# ]

REMOVE_PARAMETERS = [
    "Secchi depth",
    ######################################################################################
    "Section sediment cover",
    "Section hard clay cover",
    "Section soft clay cover",
    "Section silt cover",
    "Section silt clay cover",
    "Section silt soft clay cover",
    "Section silt cover",
    "Section sand cover",
    "Section gravel fine medium cover",
    "Section gravel coarse cover",
    "Section cobble medium cover",
    "Section cobble coarse cover",
    "Section large boulder cover",
    "Section rock cover",
    "Section shell gravel cover",
    "Section shell cover",
    "Section bare substrate cover",
    "Section debris cover",
    "Section detritus cover",
    "Section unidentified substrate cover",
    "Section epi zostera cover",
    "Section unidentified plantae cover",
    "Section nassarius tracks cover",
    "Section paguridae tracks cover",
    "Section animalia burrows cover",
    "Section animalia tracks cover",
    "Section unidentified algae cover",
    "Sediment depos cover",
    "Section boulder cover",
    "Section gravel cover",
    "Section stone cover",
    ######################################################################################
    "Loss on ignition",
    "Sediment dry weight content",
    "Sediment water content",
    "Redox potential",
    "Sediment colour code",
    "Sediment sieve fraction",
    ######################################################################################
    "Depth distribution (max depth)",
    "Large boulder cover",
    "Rock cove",
    "Sand cover",
    "Silt cover",
    ######################################################################################
    "QFLAG Secchi depth",
    ######################################################################################
    "H2S smell",
######################################################################################
    "Substrate",
    "Substrate cover",
    "Section substrate",
    "Section substrate cover",
    "Sediment deposition cover",
    "Species distribution min depth",
    "Species distribution max depth",
    "Depth distribution (max depth)",
    "Substrate specific cover",
    "Substrate cover",
    "Sediment cover",
    "Hard clay cover",
    "Soft clay cover",
    "Silt cover",
    "Sand cover",
    "Silt clay cover",
    "Gravel fine medium cover",
    "Gravel coarse cover",
    "Cobble medium cover",
    "Cobble coarse cover",
    "Large boulder cover",
    "Rock cove",
    "Shell gravel cover",
    "Shell cover",
    "Bare substrate cover",
    "Debris cover",
    "Detritus cover",
    "Unidentified substrate cover",
    "Total cover of all species",


]

COMMENT_COLUMNS = [
    ".*comment.*",
    ".*comnt.*",
    "shark_sample_id",
    "shark_sample_id_md5",
    "shark_transect_id_md5",
    "station_cluster",
    "station_marking",
]

OTHER_COLUMNS = [
    "sediment_type",
    "oxidized_layer_cm",

    "sect_substrate",
    # "sect_substrate_comment",
    "substrate",
#     "substrate_comment",
    "sediment_deposition_code",
#     "sediment_comment",
    "bottom_slope_deg",
#     "transect_comment",
    "sample_substrate_cover_boulder",
    # "sample_substrate_comnt_boulder",
    "sample_substrate_cover_rock",
#     "sample_substrate_comnt_rock",
    "sample_substrate_cover_softbottom",
#     "sample_substrate_comnt_softbottom",
    "sample_substrate_cover_stone",
#     "sample_substrate_comnt_stone",
    "sample_substrate_cover_gravel",
#     "sample_substrate_comnt_gravel",
    "sample_substrate_cover_sand",
#     "sample_substrate_comnt_sand",
    "section_bare_substrate",
#     "section_comment",
    "section_substrate_cover_boulder",
#     "section_substrate_comnt_boulder",
    "section_substrate_cover_gravel",
#     "section_substrate_comnt_gravel",
    "section_substrate_cover_rock",
#     "section_substrate_comnt_rock",
    "section_substrate_cover_sand",
#     "section_substrate_comnt_sand",
    "section_substrate_cover_softbottom",
#     "section_substrate_comnt_softbottom",
    "section_substrate_cover_stone",
#     "section_substrate_comnt_stone",
    "section_debris_cover",

]

REMOVE_VALUES_FOR_COLUMNS = []
REMOVE_VALUES_FOR_COLUMNS.extend(DEPTH_COLUMNS)
REMOVE_VALUES_FOR_COLUMNS.extend(SECCHI_COLUMNS)
# REMOVE_VALUES_FOR_COLUMNS.extend(COMMENT_COLUMNS)
REMOVE_VALUES_FOR_COLUMNS.extend(OTHER_COLUMNS)

REMOVE_VALUES_FOR_PARAMETERS = []
REMOVE_VALUES_FOR_PARAMETERS.extend(REMOVE_PARAMETERS)


# COMMENT_COLUMNS = [
#     'visit_comment',
#     'sample_comment',
#     'variable_comment',
#     'sampling_method_comment_phyche',
#     'section_comment',
#     'transect_comment',
#     'calculation_comment',
#     'relative_abundance_comment',
#     'sect_substrate_comment',
#     'method_comment',
#     'sediment_comment',
#
#     'sample_substrate_comnt_boulder',
#     'sample_substrate_comnt_rock',
#     'sample_substrate_comnt_softbottom',
#     'sample_substrate_comnt_stone',
#     'sample_substrate_comnt_gravel',
#     'sample_substrate_comnt_sand',
#
#     'section_substrate_comnt_boulder',
#     'section_substrate_comnt_gravel',
#     'section_substrate_comnt_rock',
#     'section_substrate_comnt_sand',
#     'section_substrate_comnt_softbottom',
#     'section_substrate_comnt_stone',
# ]


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
