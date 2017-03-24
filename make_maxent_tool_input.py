import csv

INFILE_NAME = "maxent_out.csv"
OUTFILE_NAME = "maxent_tool_input.csv"
DELIMITER_COL = "Harmony"

def write_row(row, writer, delimiter_index):
    truncated_row = row[0:delimiter_index]
    writer.writerow(truncated_row)

with open(INFILE_NAME, "rb") as infile:
    with open(OUTFILE_NAME, "w'") as outfile:
        reader = csv.reader(infile, delimiter="\t")
        writer = csv.writer(outfile, delimiter="\t")

        # Write headers
        headers = reader.next()
        delimiter_index = headers.index(DELIMITER_COL)
        write_row(headers, writer, delimiter_index)

        # Skip weights and write in short names
        reader.next()
        write_row(headers, writer, delimiter_index)

        # Write the data
        last_seen_input = ""
        for row in reader:
            if last_seen_input == row[0]:
                row[0] = ""
            else:
                last_seen_input = row[0]
            write_row(row, writer, delimiter_index)
