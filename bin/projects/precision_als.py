from pathlib   import Path

from pandas    import DataFrame, Series

from projects  import Project, project
from serialize import load_data

GENE_FIELDS = {
	 'C9orf72': 'estado_c9',
	    'SOD1': 'estado_sod1',
	   'ATXN2': 'estado_atxn2',
}


GENE_STATUS_CATEGORIES = {
	  'Normal': 'Normal',
	'Alterado': 'Altered',
}

FOLLOWUP_FFILL_COLUMNS = [
	'portador_vmni',
	'indicacion_peg',
	'portador_peg',
	'disfagia',
	'espesante',
	'inicio_espesante',
	'supl_nutr_oral',
	'inicio_supl_nutr_oral',
	'supl_nutr_ent',
	'inicio_supl_nutr_ent',
]


def _calculate_kings_from_followups(df: DataFrame) -> Series:
	bulbar = (df[['lenguaje', 'salivacion', 'deglucion']] < 4).any(axis=1)
	upper = (df[['escritura', 'cortar_sin_peg']] < 4).any(axis=1)
	lower = df.caminar < 4
	endstage = df.indicacion_peg | (df.disnea == 0) | (df.insuf_resp < 4)
	regions = bulbar.astype(float) + upper.astype(float) + lower.astype(float)
	endstage = endstage.astype(float) * 4
	return endstage.where(endstage == 4, regions)


def _calculate_mitos_from_followups(df: DataFrame) -> Series:
	walking_selfcare = (df.caminar <= 1) | (df.vestido <= 1)
	swallowing = df.deglucion <= 1
	communicating = (df.lenguaje <= 1) | (df.escritura <= 1)
	breathing = (df.disnea <= 1) | (df.insuf_resp <= 2)
	domains  = walking_selfcare.astype(float)
	domains += swallowing.astype(float)
	domains += communicating.astype(float)
	domains += breathing.astype(float)
	return domains


@project(name='precision_als')
class PrecisionALS(Project):

	def __init__(self, datadir: Path):
		self._patients = load_data(datadir, 'ufmn/patients')
		self._cases = self._patients[self._patients.fecha_dx.notna()]

		self._als_data  = load_data(datadir, 'ufmn/als_data')
		self._resp_data = load_data(datadir, 'ufmn/resp_data')
		self._nutr_data = load_data(datadir, 'ufmn/nutr_data')

		self._urg_episodes = load_data(datadir, 'hub_urg/episodes')
		self._urg_diagnoses = load_data(datadir, 'hub_urg/diagnoses')

		self._hosp_episodes = load_data(datadir, 'hub_hosp/episodes')
		self._hosp_diagnoses = load_data(datadir, 'hub_hosp/diagnoses')

		followups = self._als_data.merge(self._nutr_data, how='outer', on=['id_paciente', 'fecha_visita'])
		followups = followups.merge(self._resp_data, how='outer', on=['id_paciente', 'fecha_visita'])
		followups.loc[:, FOLLOWUP_FFILL_COLUMNS].ffill(inplace=True)
		self._followups = followups

		self._followups['kings_c'] = _calculate_kings_from_followups(followups)
		self._followups['mitos_c'] = _calculate_mitos_from_followups(followups)

	def describe(self) -> None:
		print()
		print(' .:: PRECISION ALS ::.')
		print()

		print(' Biogen Extant Task 1')
		print(' --------------------')
		print(f' > Total number of cases: {len(self._cases)}')
		print(f' > Current number of living cases: {len(self._cases[~self._cases.exitus])}')

		gene_info = self._cases[self._cases[GENE_FIELDS.values()].notna().any(axis=1)]
		print(f' > Number of cases with some genetic data available: {len(gene_info)}')
		for name, field in GENE_FIELDS.items():
			print(f'\t * {name} -> {sum(gene_info[field].notna())} (altered: {sum(gene_info[field] == "Alterado")})')
		print()

		print(' Biogen Extant Task 2')
		print(' --------------------')
		print(' > Number of cases with follow-up data available:')
		print(f'\t * 1+ follow-up -> {len(self._followups.value_counts("id_paciente"))}')
		print(f'\t * 2+ follow-up -> {sum(self._followups.value_counts("id_paciente") >= 2)}')
		print()

		print(' Biogen Extant Task 3')
		print(' --------------------')
		print(f' > Time to ambulation support: {len(self._als_data[self._als_data.caminar <= 2].value_counts("id_paciente"))}')
		print(f' > Time to CPAP: {len(self._resp_data[self._resp_data.inicio_cpap.notna()].value_counts("id_paciente"))}')
		print(f' > Time to VMNI: {len(self._resp_data[self._resp_data.inicio_vmni.notna()].value_counts("id_paciente"))}')
		print(f' > Time to PEG: {len(self._nutr_data[self._nutr_data.fecha_indicacion_peg.notna()].value_counts("id_paciente"))}')
		print(f' > Time to MiToS: {len(self._followups[self._followups.mitos_c.notna()].value_counts("id_paciente"))}')
		for n in range(5):
			print(f'\t * Stage {n} -> {len(self._followups[self._followups.mitos_c == n].value_counts("id_paciente"))}')
		print(f' > Time to King\'s: {len(self._followups[self._followups.kings_c.notna()].value_counts("id_paciente"))}')
		for n in range(5):
			print(f'\t * Stage {n} -> {len(self._followups[self._followups.kings_c == n].value_counts("id_paciente"))}')
		print(f' > Time to death: {len(self._cases[self._cases.fecha_exitus.notna()])}')
		print()

		print(' Biogen Extant Task 4')
		print(' --------------------')
		print(f' > Patients on Riluzole: {sum(self._cases.riluzol.fillna(False))}')
		print(f' > Time to Riluzole data available: {sum(self._cases.inicio_riluzol.notna())}')
		print(f' > Patients with symptomatic treatment data available: (pending)')
		print()

		print(' Biogen Extant Task 5')
		print(' --------------------')
		print(f' > Patients with hospitalization data available: {len(self._cases[self._cases.nhc.notna()])}')
		print(f' > Patients with ER consultation data available: {len(self._cases[self._cases.nhc.notna()])}')
		print()

		print(' Biogen Extant Task 6')
		print(' --------------------')
		print(f' > Patients with working status data available: (pending)')
		print(f' > Patients with level of assistance data available: (pending)')
		print()

	def export_data(self) -> DataFrame:

		return DataFrame({

			'site': 'Bellvitge Barcelona',
			'patient_id': self._cases.cip,

			'birthdate': self._cases.fecha_nacimiento,
			'sex': self._cases.sexo.map({ 'Hombre': 'Male', 'Mujer': 'Female' }),

			'c9_status': self._cases.estado_c9.map(GENE_STATUS_CATEGORIES),
			'sod1_status': self._cases.estado_sod1.map(GENE_STATUS_CATEGORIES),
			'fus_status': None,
			'tardbp_status': None,

			'clinical_onset': self._cases.inicio_clinica,
			'als_dx': self._cases.fecha_dx,

			'kings_0': self._followups[self._followups.kings_c == 0].groupby('id_paciente').fecha_visita.min(),
			'kings_1': self._followups[self._followups.kings_c == 1].groupby('id_paciente').fecha_visita.min(),
			'kings_2': self._followups[self._followups.kings_c == 2].groupby('id_paciente').fecha_visita.min(),
			'kings_3': self._followups[self._followups.kings_c == 3].groupby('id_paciente').fecha_visita.min(),
			'kings_4': self._followups[self._followups.kings_c == 4].groupby('id_paciente').fecha_visita.min(),

			'mitos_0': self._followups[self._followups.mitos_c == 0].groupby('id_paciente').fecha_visita.min(),
			'mitos_1': self._followups[self._followups.mitos_c == 1].groupby('id_paciente').fecha_visita.min(),
			'mitos_2': self._followups[self._followups.mitos_c == 2].groupby('id_paciente').fecha_visita.min(),
			'mitos_3': self._followups[self._followups.mitos_c == 3].groupby('id_paciente').fecha_visita.min(),
			'mitos_4': self._followups[self._followups.mitos_c == 4].groupby('id_paciente').fecha_visita.min(),

			'death': self._cases.fecha_exitus,

			'alsfrs_dx': None,
			'alsfrs_dx_y1': None,
			'alsfrs_dx_y2': None,
			'alsfrs_dx_y3': None,
			'alsfrs_dx_y4': None,
			'alsfrs_dx_y5': None,

			'alsfrs_bulbar_dx': None,
			'alsfrs_bulbar_dx_y1': None,
			'alsfrs_bulbar_dx_y2': None,
			'alsfrs_bulbar_dx_y3': None,
			'alsfrs_bulbar_dx_y4': None,
			'alsfrs_bulbar_dx_y5': None,

			'vmni_initiation': None,
			'peg_initiation': None,
			'oral_supl_initiation': None,
			'enteric_supl_initiation': None,

			'riluzole_received': self._cases.riluzol,
			'riluzole_initiation': self._cases.inicio_riluzol,

			'fvc_sitting_baseline': None,
			'fvc_sitting_dx_y1': None,
			'fvc_sitting_dx_y2': None,
			'fvc_sitting_dx_y3': None,
			'fvc_sitting_dx_y4': None,
			'fvc_sitting_dx_y5': None,

			'fvc_lying_baseline': None,
			'fvc_lying_dx_y1': None,
			'fvc_lying_dx_y2': None,
			'fvc_lying_dx_y3': None,
			'fvc_lying_dx_y4': None,
			'fvc_lying_dx_y5': None,

		})
