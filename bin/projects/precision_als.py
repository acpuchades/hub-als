import csv
from pathlib   import Path

from pandas    import DataFrame

from serialize import load_data


EXPORT_COLUMN_NAMES = [

]


def load_patient_data(datadir: Path, name: str, patients: DataFrame):
	df = load_data(datadir, name)
	df = df.merge(patients, left_on='pid', right_index=True)
	return df

def export_data(datadir: Path, output: Path) -> None:
	patients  = load_data(datadir, 'ufmn/patients')
	als_data  = load_patient_data(datadir, 'ufmn/als_data', patients)
	resp_data = load_patient_data(datadir, 'ufmn/resp_data', patients)
	nutr_data = load_patient_data(datadir, 'ufmn/nutr_data', patients)

	with open(output, 'w', newline='') as outf:
		writer = csv.DictWriter(outf, fieldnames=EXPORT_COLUMN_NAMES)
		writer.writeheader()
		writer.writerows({
			'site': 'Bellvitge Barcelona',
			'patient_id': patients.cip,

			'birthdate': patients.fecha_nacimiento,
			'sex': patients.sexo,

			'c9_status': patients.c9_status,
			'sod1_status': patients.sod1_status,
			'fus_status': patients.fus_status,
			'tardbp_status': patients.tardbp_status,

			'clinical_onset': patients.inicio_clinica,
			'als_dx': patients.fecha_diagnostico,

			'kings_1': als_data[als_data.kings == 1].groupby('pid').fecha_visita.min(),
			'kings_2': als_data[als_data.kings == 2].groupby('pid').fecha_visita.min(),
			'kings_3': als_data[als_data.kings == 3].groupby('pid').fecha_visita.min(),
			'kings_4': als_data[als_data.kings == 4].groupby('pid').fecha_visita.min(),

			'mitos_1': als_data[als_data.mitos == 1].groupby('pid').fecha_visita.min(),
			'mitos_2': als_data[als_data.mitos == 2].groupby('pid').fecha_visita.min(),
			'mitos_3': als_data[als_data.mitos == 3].groupby('pid').fecha_visita.min(),
			'mitos_4': als_data[als_data.mitos == 4].groupby('pid').fecha_visita.min(),

			'death': patients.fecha_exitus,

			'alsfrs_baseline': None,
			'alsfrs_dx_y1': None,
			'alsfrs_dx_y2': None,
			'alsfrs_dx_y3': None,
			'alsfrs_dx_y4': None,
			'alsfrs_dx_y5': None,

			'alsfrs_resp_baseline': None,
			'alsfrs_bulbar_dx_y1': None,
			'alsfrs_bulbar_dx_y2': None,
			'alsfrs_bulbar_dx_y3': None,
			'alsfrs_bulbar_dx_y4': None,
			'alsfrs_bulbar_dx_y5': None,

			'vmni_initiation': None,
			'peg_initiation': None,
			'oral_supl_initiation': None,
			'enteric_supl_initiation': None,

			'riluzole_received': None,
			'riluzole_initiation': None,

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


def describe(datadir: Path) -> None:
	patients  = load_data(datadir, 'ufmn/patients')
	als_data  = load_patient_data(datadir, 'ufmn/als_data', patients)
	resp_data = load_patient_data(datadir, 'ufmn/resp_data', patients)
	nutr_data = load_patient_data(datadir, 'ufmn/nutr_data', patients)

	cases = patients[patients.fecha_dx != False]
	gene_cases = cases[cases.c9_status.notna() | cases.sod1_status.notna() | cases.atxn2_status.notna()]

	print()
	print(' .:: PRECISION ALS ::.')
	print()

	print(' Biogen Extant Task 1')
	print(' --------------------')
	print(f' > Total number of cases: {len(cases)}')
	print(f' > Current number of living cases: {len(cases[~cases.exitus])}')
	print(f' > Number of cases with genetic testing available: {len(gene_cases)}')
	print(f'\t* C9orf72 -> {len(cases[cases.c9_status.notna()])} (positive: {len(cases[cases.c9_status == "Alterado"])})')
	print(f'\t* SOD1 -> {len(cases[cases.sod1_status.notna()])} (positive: {len(cases[cases.sod1_status == "Alterado"])})')
	print(f'\t* ATXN2 -> {len(cases[cases.atxn2_status.notna()])} (positive: {len(cases[cases.atxn2_status == "Alterado"])})')
	print()

	print(' Biogen Extant Task 2')
	print(' --------------------')
	print(' > Number of cases with follow-up data available:')
	print(f'\t* 1+ follow-up -> {len(als_data.value_counts("pid"))}')
	print(f'\t* 2+ follow-up -> {sum(als_data.value_counts("pid") >= 2)}')
	print()

	print(' Biogen Extant Task 3')
	print(' --------------------')
	print(f' > Time to ambulation support: {len(als_data[als_data.caminar <= 2].value_counts("pid"))}')
	print(f' > Time to CPAP: {len(resp_data[resp_data.cpap.fillna(False)].value_counts("pid"))}')
	print(f' > Time to VMNI: {len(resp_data[resp_data.portador_vmni.fillna(False)].value_counts("pid"))}')
	print(f' > Time to PEG: {len(nutr_data[nutr_data.indicacion_peg.fillna(False)].value_counts("pid"))}')
	print(f' > Time to death: {len(cases[~cases.fecha_exitus.isna()])}')
	print()

	print(' Biogen Extant Task 4')
	print(' --------------------')
	print(f' > Patients on Riluzole: {len(cases[cases.riluzol.fillna(False)])}')
	print(f' > Time to Riluzole: {len(cases[~cases.inicio_riluzol.isna()])}')
	print()

	print(' Biogen Extant Task 6')
	print(' --------------------')
	print(f' > Patients currently working: {len(cases[cases.situacion_activa])}')
	print()