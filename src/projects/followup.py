from pathlib import Path

from pandas import DataFrame, Series
from projects import Project, project
from serialize import load_data


FFILL_COLUMNS = [
	'portador_vmni',
	'indicacion_peg',
	'portador_peg',
	'disfagia',
	'espesante',
	'inicio_espesante',
	'supl_oral',
	'inicio_supl_oral',
	'supl_enteral',
	'inicio_supl_enteral',
]

ALSFRS_TOTAL_COLUMNS = [
	'lenguaje',
	'salivacion',
	'deglucion',
	'escritura',
	'cortar',
	'vestido',
	'cama',
	'caminar',
	'subir_escaleras',
	'disnea',
	'ortopnea',
	'insuf_resp',
]

ALSFRS_BULBAR_COLUMNS = [
	'lenguaje',
	'salivacion',
	'deglucion',
]

ALSFRS_MOTORF_COLUMNS = [
	'escritura',
	'cortar',
	'vestido',
]

ALSFRS_MOTORG_COLUMNS = [
	'cama',
	'caminar',
	'subir_escaleras',
]

ALSFRS_RESP_COLUMNS = [
	'disnea',
	'ortopnea',
	'insuf_resp',
]

EXPORT_COLUMNS = [
	'nhc',
	'fecha_visita',
	'lenguaje',
	'salivacion',
	'deglucion',
	'escritura',
	'cortar_sin_peg',
	'cortar_con_peg',
	'cortar',
	'vestido',
	'cama',
	'caminar',
	'subir_escaleras',
	'disnea',
	'ortopnea',
	'insuf_resp',
	'alsfrs_total',
	'alsfrs_total_c',
	'alsfrs_bulbar',
	'alsfrs_bulbar_c',
	'alsfrs_motorf_c',
	'alsfrs_motorg_c',
	'alsfrs_resp_c',
	'indicacion_peg',
	'portador_peg',
	'kings',
	'kings_c',
	'mitos',
	'mitos_c',
]


def _calculate_kings_from_followup(df: DataFrame) -> Series:
	bulbar = (df[['lenguaje', 'salivacion', 'deglucion']] < 4).any(axis=1)
	upper = (df[['escritura', 'cortar_sin_peg']] < 4).any(axis=1)
	lower = df.caminar < 4
	endstage = df.indicacion_peg | (df.disnea == 0) | (df.insuf_resp < 4)
	regions = bulbar.astype('Int64') + upper.astype('Int64') + lower.astype('Int64')
	endstage = endstage.astype('Int64') * 4
	return endstage.where(endstage == 4, regions)


def _calculate_mitos_from_followup(df: DataFrame) -> Series:
	walking_selfcare = (df.caminar <= 1) | (df.vestido <= 1)
	swallowing = df.deglucion <= 1
	communicating = (df.lenguaje <= 1) | (df.escritura <= 1)
	breathing = (df.disnea <= 1) | (df.insuf_resp <= 2)
	domains = walking_selfcare.astype('Int64')
	domains += swallowing.astype('Int64')
	domains += communicating.astype('Int64')
	domains += breathing.astype('Int64')
	return domains

def load_followup_data(datadir: Path = None, als_data: DataFrame = None, resp_data: DataFrame = None, nutr_data: DataFrame = None):
	als_data = als_data if als_data is not None else load_data(datadir, 'ufmn/als_data')
	nutr_data = nutr_data if nutr_data is not None else load_data(datadir, 'ufmn/nutr_data')
	resp_data = resp_data if resp_data is not None else load_data(datadir, 'ufmn/resp_data')

	followups = als_data.merge(nutr_data, how='outer', on=['id_paciente', 'fecha_visita'])
	followups = followups.merge(resp_data, how='outer', on=['id_paciente', 'fecha_visita'])
	followups[FFILL_COLUMNS] = followups.groupby('id_paciente')[FFILL_COLUMNS].ffill()
	followups.dropna(subset=['id_paciente', 'fecha_visita'], inplace=True)

	followups = followups.set_index(['id_paciente', 'fecha_visita'])  \
	                     .groupby(level=[0, 1]).bfill().reset_index() \
	                     .drop_duplicates(['id_paciente', 'fecha_visita'])

	followups['cortar'] = None
	followups.cortar = followups[followups.portador_peg.fillna(False)].cortar_con_peg
	followups.cortar = followups[~followups.portador_peg.fillna(False)].cortar_sin_peg

	followups['kings_c'] = _calculate_kings_from_followup(followups)
	followups['mitos_c'] = _calculate_mitos_from_followup(followups)

	followups['alsfrs_bulbar_c'] = followups[ALSFRS_BULBAR_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	followups['alsfrs_motorf_c'] = followups[ALSFRS_MOTORF_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	followups['alsfrs_motorg_c'] = followups[ALSFRS_MOTORG_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	followups['alsfrs_resp_c'] = followups[ALSFRS_RESP_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	followups['alsfrs_total_c'] = followups[ALSFRS_TOTAL_COLUMNS].sum(axis=1, skipna=False).astype('Int64')

	return followups


@project('followup')
class FollowUp(Project):

	def __init__(self, datadir: Path):
		followups = load_followup_data(datadir)
		patients = load_data(datadir, 'ufmn/patients')
		self._followups = followups.merge(patients, on='id_paciente')

	def export_data(self) -> DataFrame:
		return self._followups[EXPORT_COLUMNS].reset_index(drop=True)