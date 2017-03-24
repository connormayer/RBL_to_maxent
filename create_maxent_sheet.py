# This script takes the output from the Albright & Hayes Rule Based Learner and
# converts it to an Excel spreadsheet that can be used to train a MaxEnt model.
# This is quick and dirty, and not very efficient.

import csv

DO_CONTEXTS = True
DO_WUGS = False

INFILE_NAME = 'CELEXFull.in'
SUMFILE_NAME = 'CELEXFull_c75i75.sum'
WUGSUM_NAME = 'CELEXFull_with_wugs_c75i75.sum'
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
    if DO_CONTEXTS:
        change = item[2].split(",")[0].split("(")[1]
    else:
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

def get_maxent_cols(item, constraint_list, sorted_violations, row_count,
                    nonwug_violations=None):
    constraints_length = len(constraint_list)
    headers_length = constraints_length + len(MAXENT_HEADERS)
    row_length = CONSTRAINTS_OFFSET + headers_length
    starting_col = colnum_string(CONSTRAINTS_OFFSET + 1)
    end_col = colnum_string(CONSTRAINTS_OFFSET + constraints_length)
    weights_start = "{}${}".format(starting_col, WEIGHTS_ROW)
    weights_end = "{}${}".format(end_col, WEIGHTS_ROW)

    row_count += 1
    row = [""] * row_length

    # Set input, output, and frequency
    row[0] = item[0]
    row[1] = item[1]
    row[2] = freq_dict.get((item[0], item[1]), "0")
    row[CONSTRAINTS_OFFSET + constraint_list.index(item[2])] = "1"

    # Get information needed for Observed
    # This is brutally inefficient
    freq_count = 0

    if nonwug_violations:
        wug_offset = len(nonwug_violations)
    else:
        wug_offset = 0

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
    i = row_count - HEADERS_OFFSET - 1 - wug_offset
    min_row = i + HEADERS_OFFSET + 1 + wug_offset
    max_row = i + HEADERS_OFFSET + 1 + wug_offset

    # Get the range of rows corresponding to the same input form
    while i >= 0 and sorted_violations[i - 1][0] == item[0]:
        i -= 1
        min_row = i + HEADERS_OFFSET + 1 + wug_offset
    i = row_count - HEADERS_OFFSET - 1 - wug_offset
    while i + 1 < len(sorted_violations) and sorted_violations[i + 1][0] == item[0]:
        i += 1
        max_row = i + HEADERS_OFFSET + 1 + wug_offset

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

    return row, row_count

def write_wugs(constraint_list, constraint_violations, row_count, writer,
               nonwug_violations):
    sorted_violations = sorted(constraint_violations)
    sorted_violations = [
        item for item in sorted_violations if is_good_application(item)
    ]

    number_of_candidates = len(sorted_violations)

    for item in sorted_violations:
        row,row_count = get_maxent_cols(
            item, constraint_list, sorted_violations, row_count,
            nonwug_violations
        )
        writer.writerow(row)

def build_output_file(constraint_list, constraint_violations,
                      wug_constraint_violations, freq_dict):
    constraints_length = len(constraint_list)
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
        sorted_violations = [
            item for item in sorted_violations if is_good_application(item)
        ]

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
            row, row_count = get_maxent_cols(
                    item, constraint_list, sorted_violations, row_count
            )
            writer.writerow(row)

        if DO_WUGS:
            write_wugs(
                constraint_list, wug_constraint_violations, row_count, writer,
                sorted_violations
            )

def remove_duplicates(my_list):
    new_list = []
    for item in my_list:
        if item not in new_list:
            new_list.append(item)
    return new_list

def build_constraints_list(reader):
    # Skip headers
    reader.next()

    constraint_violations = []
    constraint_list = []

    for row in reader:
        # Get change
        input_form = row[3]
        output_form = row[5]
        change = row[10]
        change_parts = change.split("/")

        # Get rid of morphological type
        change = "/".join(change_parts[:2])

        # Get context
        pfeat = row[13]
        P = row[14]
        Q = row[16]
        qfeat = row[17]

        # TODO: Deal with impugnment
        if DO_CONTEXTS:
            constraint_name = "*MAP({},{}{}__{}{})".format(
                change, pfeat, P, Q, qfeat
            )
        else:
            constraint_name = "*MAP({})".format(change)

        constraint_violations.append(
            [input_form, output_form, constraint_name]
        )
        if constraint_name not in constraint_list:
            constraint_list.append(constraint_name)

    return constraint_list, constraint_violations

with open(INFILE_NAME, 'rb') as freq_file:
    with open(SUMFILE_NAME, 'rb') as input_file:
        reader = csv.reader(input_file, delimiter="\t")
        freq_dict = build_freq_dict(freq_file)
        constraint_list, constraint_violations = build_constraints_list(reader)

        with open(WUGSUM_NAME, 'rb') as wug_file:
            reader = csv.reader(wug_file, delimiter="\t")
            wug_constraint_list, wug_constraint_violations = build_constraints_list(reader)
            # Combine constraints needed for wugs with those needed for regular 
            # Remove duplicates
            constraint_list = list(set(constraint_list + wug_constraint_list))

            # Remove duplicates from wug forms, there are a bunch in the provided
            # input files.
            wug_constraint_violations = remove_duplicates(wug_constraint_violations)
            constraint_violations = remove_duplicates(constraint_violations)

            build_output_file(
                constraint_list, constraint_violations,
                wug_constraint_violations, freq_dict
            )
