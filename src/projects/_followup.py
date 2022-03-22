from pathlib import Path

import pandas as pd

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


def _calculate_kings_from_followup(df: pd.DataFrame) -> pd.Series:
	bulbar = (df[['lenguaje', 'salivacion', 'deglucion']] < 4).any(axis=1)
	upper = (df[['escritura', 'cortar_sin_peg']] < 4).any(axis=1)
	lower = df.caminar < 4
	endstage = df.indicacion_peg | (df.disnea == 0) | (df.insuf_resp < 4)
	regions = bulbar.astype('Int64') + upper.astype('Int64') + lower.astype('Int64')
	endstage = endstage.astype('Int64') * 4
	return endstage.where(endstage == 4, regions)


def _calculate_mitos_from_followup(df: pd.DataFrame) -> pd.Series:
	walking_selfcare = (df.caminar <= 1) | (df.vestido <= 1)
	swallowing = df.deglucion <= 1
	communicating = (df.lenguaje <= 1) | (df.escritura <= 1)
	breathing = (df.disnea <= 1) | (df.insuf_resp <= 2)
	domains = walking_selfcare.astype('Int64')
	domains += swallowing.astype('Int64')
	domains += communicating.astype('Int64')
	domains += breathing.astype('Int64')
	return domains


def _add_calculated_fields(df: pd.DataFrame) -> None:
	df['cortar'] = None
	df.cortar = df[df.portador_peg.fillna(False)].cortar_con_peg
	df.cortar = df[~df.portador_peg.fillna(False)].cortar_sin_peg

	df['kings_c'] = _calculate_kings_from_followup(df)
	df['mitos_c'] = _calculate_mitos_from_followup(df)

	df['alsfrs_bulbar_c'] = df[ALSFRS_BULBAR_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	df['alsfrs_motorf_c'] = df[ALSFRS_MOTORF_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	df['alsfrs_motorg_c'] = df[ALSFRS_MOTORG_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	df['alsfrs_resp_c'] = df[ALSFRS_RESP_COLUMNS].sum(axis=1, skipna=False).astype('Int64')
	df['alsfrs_total_c'] = df[ALSFRS_TOTAL_COLUMNS].sum(axis=1, skipna=False).astype('Int64')


def load_followup_data(datadir: Path = None, als_data: pd.DataFrame = None,
                       resp_data: pd.DataFrame = None, nutr_data: pd.DataFrame = None):

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

	_add_calculated_fields(followups)

	return followups


def resample_followup_data(df: pd.DataFrame, start: pd.Series, freq: str):

	def _resample_helper(group: pd.DataFrame):
		assert(group.id_paciente.nunique() == 1)
		pid = group.iloc[0].id_paciente
		end = group.index.max()
		begin = None
		if pid in start.index:
			begin = start[pid]
		if pd.isna(begin):
			begin = end
		index = pd.date_range(name='fecha', start=begin, end=end, freq='D')
		return group.reindex(index).ffill().asfreq(freq)

	df = df.set_index('fecha_visita').groupby('id_paciente').apply(_resample_helper)
	df = df.drop('id_paciente', axis=1).reset_index()
	return df