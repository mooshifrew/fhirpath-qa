# Template Reference

This document provides a comprehensive reference for all FHIR-QA templates, organized by their source files and numbered sequentially.

## Template Groups

### 1. Count Templates (`counts.py`)
Templates for counting various medical events and resources.

| # | Template ID | Question Template |
|---|-------------|-------------------|
| 001 | count-drugs-prescribed | Count the number of drugs patient {patient_id} were prescribed [time_filter_global1]. |
| 002 | count-hospital-visits | Count the number of hospital visits of patient {patient_id} [time_filter_global1]. |
| 003 | count-icu-visits | Count the number of ICU visits of patient {patient_id} [time_filter_global1]. |
| 004 | count-input-intake-events | Count the number of times that patient {patient_id} had a {input_name} intake [time_filter_global1]. |
| 005 | count-output-events | Count the number of times that patient {patient_id} had a {output_name} output [time_filter_global1]. |
| 006 | count-lab-test-events | Count the number of times that patient {patient_id} received a {lab_name} lab test [time_filter_global1]. |
| 007 | count-procedure-events | Count the number of times that patient {patient_id} received a {procedure_name} procedure [time_filter_global1]. |
| 008 | count-specific-drug-prescriptions | Count the number of times that patient {patient_id} were prescribed {drug_name} [time_filter_global1]. |

### 2. Has/Boolean Templates (`has_verb.py`)
Templates for checking the existence of medical events and conditions.

| # | Template ID | Question Template |
|---|-------------|-------------------|
| 009 | has-hospital-admission | Has_verb patient {patient_id} been admitted to the hospital [time_filter_global1]? |
| 010 | has-diagnosis | Has_verb patient {patient_id} been diagnosed with {diagnosis_name} [time_filter_global1]? |
| 011 | has-drug-prescribed | Has_verb patient {patient_id} been prescribed {drug_name} [time_filter_global1]? |
| 012 | has-multiple-drugs-or | Has_verb patient {patient_id} been prescribed {drug_name1}, {drug_name2}, or {drug_name3} [time_filter_global1]? |
| 013 | has-any-medication | Has_verb patient {patient_id} been prescribed any medication [time_filter_global1]? |
| 014 | has-emergency-room-visit | Has_verb patient {patient_id} been to an emergency room [time_filter_global1]? |
| 015 | has-input-intake | Has_verb patient {patient_id} had any {input_name} intake [time_filter_global1]? |
| 016 | has-output-events | Has_verb patient {patient_id} had any {output_name} output [time_filter_global1]? |
| 017 | has-micro-test-specific | Has_verb patient {patient_id} had any {spec_name} microbiology test result [time_filter_global1]? |
| 018 | has-micro-test-any | Has_verb patient {patient_id} had any microbiology test result [time_filter_global1]? |
| 019 | has-lab-test | Has_verb patient {patient_id} received a {lab_name} lab test [time_filter_global1]? |
| 020 | has-procedure | Has_verb patient {patient_id} received a {procedure_name} procedure [time_filter_global1]? |
| 021 | has-any-diagnosis | Has_verb patient {patient_id} received any diagnosis [time_filter_global1]? |
| 022 | has-any-lab-test | Has_verb patient {patient_id} received any lab test [time_filter_global1]? |
| 023 | has-any-procedure | Has_verb patient {patient_id} received any procedure [time_filter_global1]? |
| 024 | has-vital-comparison | Has_verb the {vital_name} of patient {patient_id} been ever [comparison] than {vital_value} [time_filter_global1]? |
| 025 | has-normal-vital | Has_verb the {vital_name} of patient {patient_id} been normal [time_filter_global1]? |
| 026 | has-organism-found | Has_verb there been any organism found in the [time_filter_exact1] {spec_name} microbiology test of patient {patient_id} [time_filter_global1]? |

### 3. List Templates (`list_queries.py`)
Templates for listing or retrieving multiple values.

| # | Template ID | Question Template |
|---|-------------|-------------------|
| 027 | list-admission-times | List the hospital admission time of patient {patient_id} [time_filter_global1]. |

### 4. Specific Date Templates (`specific_dates.py`)
Templates for retrieving specific date/time information.

| # | Template ID | Question Template |
|---|-------------|-------------------|
| 028 | time-micro-test-specific | When was patient {patient_id}'s [time_filter_exact1] {spec_name} microbiology test [time_filter_global1]? |
| 029 | time-hospital-admission | When was the [time_filter_exact1] hospital admission time of patient {patient_id}? |
| 030 | time-admission-route | When was the [time_filter_exact1] hospital admission time that patient {patient_id} was admitted via {admission_route}? |
| 031 | time-hospital-discharge | When was the [time_filter_exact1] hospital discharge time of patient {patient_id}? |
| 032 | time-intake | When was the [time_filter_exact1] intake time of patient {patient_id} [time_filter_global1]? |
| 033 | time-lab-test | When was the [time_filter_exact1] lab test of patient {patient_id} [time_filter_global1]? |
| 034 | time-micro-test | When was the [time_filter_exact1] microbiology test of patient {patient_id} [time_filter_global1]? |
| 035 | time-prescription | When was the [time_filter_exact1] prescription time of patient {patient_id} [time_filter_global1]? |
| 036 | time-procedure | When was the [time_filter_exact1] procedure time of patient {patient_id} [time_filter_global1]? |
| 037 | time-specific-intake | When was the [time_filter_exact1] time that patient {patient_id} had a {input_name} intake [time_filter_global1]? |
| 038 | time-specific-output | When was the [time_filter_exact1] time that patient {patient_id} had a {output_name} output [time_filter_global1]? |
| 039 | time-vital-measurement | When was the [time_filter_exact1] time that patient {patient_id} had a {vital_name} measured [time_filter_global1]? |
| 040 | time-specific-lab | When was the [time_filter_exact1] time that patient {patient_id} received a {lab_name} lab test [time_filter_global1]? |
| 041 | time-specific-procedure | When was the [time_filter_exact1] time that patient {patient_id} received a {procedure_name} procedure [time_filter_global1]? |
| 042 | time-specific-diagnosis | When was the [time_filter_exact1] time that patient {patient_id} was diagnosed with {diagnosis_name} [time_filter_global1]? |
| 043 | time-specific-drug | When was the [time_filter_exact1] time that patient {patient_id} was prescribed {drug_name} [time_filter_global1]? |
| 044 | time-drug-route | When was the [time_filter_exact1] time that patient {patient_id} was prescribed a medication via {drug_route} route [time_filter_global1]? |

### 5. Specific Value Templates (`specific_values.py`)
Templates for retrieving specific values and measurements.

| # | Template ID | Question Template |
|---|-------------|-------------------|
| 045 | patient-birth-date | What is the date of birth of patient {patient_id}? |
| 046 | patient-gender | What is the gender of patient {patient_id}? |
| 047 | careunit | What was the [time_filter_exact1] careunit of patient {patient_id} [time_filter_global1]? |
| 048 | admission-type | What was the [time_filter_exact1] hospital admission type of patient {patient_id}? |
| 049 | vital-measurement | What was the [time_filter_exact1] measured {vital_name} of patient {patient_id} [time_filter_global1]? |
| 050 | lab-measurement | What was the [time_filter_exact1] measured value of a {lab_name} lab test of patient {patient_id} [time_filter_global1]? |
| 051 | weight | What was the [time_filter_exact1] measured weight of patient {patient_id} [time_filter_global1]? |
| 052 | drug-dose | What was the dose of {drug_name} that patient {patient_id} was [time_filter_exact1] prescribed [time_filter_global1]? |
| 053 | diagnosis-name | What was the name of the diagnosis that patient {patient_id} [time_filter_exact1] received [time_filter_global1]? |
| 054 | drug-name | What was the name of the drug that patient {patient_id} was [time_filter_exact1] prescribed [time_filter_global1]? |
| 055 | drug-name-route | What was the name of the drug that patient {patient_id} was [time_filter_exact1] prescribed via {drug_route} route [time_filter_global1]? |
| 056 | lab-name | What was the name of the lab test that patient {patient_id} [time_filter_exact1] received [time_filter_global1]? |
| 057 | micro-test-name | What was the name of the microbiology test that patient {patient_id} [time_filter_exact1] received [time_filter_global1]? |
| 058 | output-name | What was the name of the output that patient {patient_id} [time_filter_exact1] had [time_filter_global1]? |
| 059 | procedure-name | What was the name of the procedure that patient {patient_id} [time_filter_exact1] received [time_filter_global1]? |
| 060 | specimen-name | What was the name of the specimen that patient {patient_id} was [time_filter_exact1] tested [time_filter_global1]? |
| 061 | organism-name | What was the organism name found in the [time_filter_exact1] {spec_name} microbiology test of patient {patient_id} [time_filter_global1]? |

## Template Placeholders

### Simple Placeholders
- `{patient_id}` - Patient identifier
- `{drug_name}` - Drug name
- `{procedure_name}` - Procedure name
- `{diagnosis_name}` - Diagnosis name
- `{lab_name}` - Lab test name
- `{vital_name}` - Vital sign name
- `{input_name}` - Input/medication name
- `{output_name}` - Output name
- `{spec_name}` - Specimen name
- `{admission_route}` - Admission route
- `{drug_route}` - Drug administration route
- `{vital_value}` - Vital sign value
- `{drug_name1}`, `{drug_name2}`, `{drug_name3}` - Multiple drug names

### Time Placeholders
- `[time_filter_global1]` - Global time filter (e.g., "in 2023", "since last month")
- `[time_filter_exact1]` - Exact time filter (e.g., "first", "last")

### Operation Placeholders
- `[comparison]` - Comparison operator (e.g., "greater", "less than")

### Verb Placeholders
- `Has_verb` - Verb for boolean questions (e.g., "Has", "Did")

