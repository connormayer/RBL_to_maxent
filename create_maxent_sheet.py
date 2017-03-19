# This script takes the output from the Albright & Hayes Rule Based Learner and
# converts it to an Excel spreadsheet that can be used to train a MaxEnt model.
# This is quick and dirty, and not very efficient.

import csv

INFILE_NAME = 'CELEXFull.in'
SUMFILE_NAME = 'CELEXFull_c75i75.sum'
OUTFILE_NAME = 'maxent_out.csv'

CONSTRAINTS_OFFSET = 3
HEADERS_OFFSET = 2
WEIGHTS_ROW = 2
FREQ_COL_NUM = 3

MAXENT_HEADERS = [
	"Harmony", "eHarmony", "Z", "prob", "Candidate", "Predicted", "Observed",
	"error", "logprob", "likelihood"
]

HARMONY_FORMULA = "=SUMPRODUCT({}:{},{}:{})"
EHARMONY_FORMULA = "=EXP(-{})"
Z_FORMULA = "=SUM({}:{})"
PROB_FORMULA = "={}/{}"
PREDICTED_FORMULA = "={}"
ERROR_FORMULA = "=ABS({}-{})"
LOG_PROB_FORMULA = "=LOG({})"
LIKELIHOOD_FORMULA = "=SUMPRODUCT({}:{},{}:{})"

def colnum_string(n):
	# Convert column number to excel column string
    div = n
    string = ""
    temp = 0
    while div > 0:
        module = (div - 1) % 26
        string = chr(65 + module) + string
        div = int((div - module) / 26)
    return string

def get_col_index(col_name, list_len):
	return CONSTRAINTS_OFFSET + list_len + MAXENT_HEADERS.index(col_name)

def is_good_application(item):
	# The rules 0 -> t, 0 -> d, and 0 -> Xd all seem to apply in all cases
	# This function checks if the application is erroneous and returns
	# False if it is, True otherwise
	change = item[2].split("(")[1].split(")")[0]

	if change == "/d" and (item[1][-1] != "d" or item[1][-2:] == "Xd"):
		return False
	elif change == "/t" and item[1][-1] != "t":
		return False
	elif change == "/Xd" and item[1][-2:] != "Xd":
		return False
	return True

def build_freq_dict(freq_file):
	freq_dict = {}
	freq_reader = csv.reader(freq_file, delimiter='\t')
	for row in freq_reader:
		if len(row) > 3:
			freq_dict[(row[0], row[1])] = row[2]
	return freq_dict

def build_output_file(constraint_list, constraint_violations, freq_dict):
	constraints_length = len(constraint_list)
	headers_length = constraints_length + len(MAXENT_HEADERS)
	row_length = CONSTRAINTS_OFFSET + headers_length
	starting_col = colnum_string(CONSTRAINTS_OFFSET + 1)
	end_col = colnum_string(CONSTRAINTS_OFFSET + constraints_length)
	weights_start = "{}${}".format(starting_col, WEIGHTS_ROW)
	weights_end = "{}${}".format(end_col, WEIGHTS_ROW)

	with open(OUTFILE_NAME, 'w') as output_file:
		writer = csv.writer(output_file, delimiter="\t")
		writer.writerow(
			[""] * CONSTRAINTS_OFFSET + constraint_list + MAXENT_HEADERS
		)
		freq_col = colnum_string(FREQ_COL_NUM)
		logprob_index = get_col_index(
			"logprob", constraints_length
		)
		logprob_col = colnum_string(logprob_index + 1)

		sorted_violations = sorted(constraint_violations)
		sorted_violations = [item for item in sorted_violations if is_good_application(item)]

		number_of_candidates = len(sorted_violations)

		likehood_value = LIKELIHOOD_FORMULA.format(
			freq_col + str(WEIGHTS_ROW + 1),
			freq_col + str(WEIGHTS_ROW + number_of_candidates),
			logprob_col + str(WEIGHTS_ROW + 1),
			logprob_col + str(WEIGHTS_ROW + number_of_candidates)
		)

		writer.writerow(
			[""] * CONSTRAINTS_OFFSET + ["0"] * len(constraint_list)
			+ [""] * (len(MAXENT_HEADERS) - 1) + [likehood_value]
		)

		row_count = HEADERS_OFFSET

		for item in sorted_violations:
			row_count += 1
			row = [""] * row_length

			# Set input, output, and frequency
			row[0] = item[0]
			row[1] = item[1]
			row[2] = freq_dict.get((item[0], item[1]), "0")
			row[CONSTRAINTS_OFFSET + constraint_list.index(item[2])] = "1"
			
			# Get information needed for Z and Observed
			# This is brutally inefficient
			freq_count = 0

			for other_item in sorted_violations:
				if (item[0] == other_item[0]):
					freq_count += int(
						freq_dict.get((other_item[0], other_item[1]), 0)
					)

			# TODO: Would be nice to loop this
			# Write in Harmony
			harmony_index = get_col_index(
				"Harmony", constraints_length
			)
			harmony = HARMONY_FORMULA.format(
				weights_start, weights_end,
				starting_col + str(row_count),
				end_col + str(row_count)
			)
			row[harmony_index] = harmony

			# Write in eHarmony
			eharmony_index = get_col_index(
				"eHarmony", constraints_length
			)
			eharmony = EHARMONY_FORMULA.format(
				colnum_string(harmony_index + 1) + str(row_count)
			)
			row[eharmony_index] = eharmony

			# Write in Z
			i = row_count - HEADERS_OFFSET - 1
			min_row = i + HEADERS_OFFSET + 1
			max_row = i + HEADERS_OFFSET + 1

			# Get the range of rows corresponding to the same input form
			while i >= 0 and sorted_violations[i - 1][0] == item[0]:
				i -= 1
				min_row = i + HEADERS_OFFSET + 1
			i = row_count - HEADERS_OFFSET - 1
			while i + 1 < len(sorted_violations) and sorted_violations[i + 1][0] == item[0]:
				i += 1
				max_row = i + HEADERS_OFFSET + 1

			# Set Z to the sum of the eHarmonies for this input
			z_index = get_col_index("Z", constraints_length)
			eharmony_col = colnum_string(eharmony_index + 1)
			z_value = Z_FORMULA.format(
				eharmony_col + str(min_row),
				eharmony_col + str(max_row)
			)
			row[z_index] = z_value

			# Write in prob
			prob_index = get_col_index("prob", constraints_length)
			prob = PROB_FORMULA.format(
				colnum_string(eharmony_index + 1) + str(row_count),
				colnum_string(z_index + 1) + str(row_count)
			)
			row[prob_index] = prob

			# Write in Candidate
			candidate_index = get_col_index(
				"Candidate", constraints_length
			)
			row[candidate_index] = item[1]

			# Write in Predicted
			predicted_index = get_col_index(
				"Predicted", constraints_length
			)
			predicted_value = PREDICTED_FORMULA.format(
				colnum_string(prob_index + 1) + str(row_count)
			)
			row[predicted_index] = predicted_value

			# Write Observed
			observed_index = get_col_index(
				"Observed", constraints_length
			)
			observed_value = float(row[2]) / freq_count if freq_count > 0 else 0
			row[observed_index] = observed_value

			# Write in Error
			error_index = get_col_index(
				"error", constraints_length
			)
			error_value = ERROR_FORMULA.format(
				colnum_string(predicted_index + 1) + str(row_count),
				colnum_string(observed_index + 1) + str(row_count)
			)
			row[error_index] = error_value

			# Write in logprob
			logprob_index = get_col_index(
				"logprob", constraints_length
			)
			logprob_value = LOG_PROB_FORMULA.format(
				colnum_string(prob_index + 1) + str(row_count)
			)
			row[logprob_index] = logprob_value

			writer.writerow(row)

with open(INFILE_NAME, 'rb') as freq_file:
	with open(SUMFILE_NAME, 'rb'
			) as input_file:
		reader = csv.reader(input_file, delimiter="\t")
		# Skip headers
		reader.next()

		constraint_violations = []
		constraint_list = []

		freq_dict = build_freq_dict(freq_file)

		for row in reader:
			input_form = row[3]
			output_form = row[5]
			change = row[10]
			change_parts = change.split("/")

			# Get rid of morphological type
			change = "/".join(change_parts[:2])

			# TODO: Get contexts
			# TODO: Deal with impugnment
			constraint_name = "*MAP({})".format(change)
			constraint_violations.append(
				[input_form, output_form, constraint_name]
			)
			if constraint_name not in constraint_list:
				constraint_list.append(constraint_name)

		build_output_file(constraint_list, constraint_violations, freq_dict)
