
RESTRICT_DATA = True


SKIP_DATA_TYPES = [
    'epibenthos',
    'epibenthos_dropvideo',
    'zoobenthos',
    'profile'
]

INCLUDE_PACKAGES = [
    'SHARK_Epibenthos_2019_OLST',
]

DEPTH_REPLACE_VALUE = '999'
COMMENT_REPLACE_VALUE = ''
SECCHI_REPLACE_VALUE = ''

DEPTH_COLUMNS = [
    'bottom_depth_m',
    'water_depth_m',
    ]

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
