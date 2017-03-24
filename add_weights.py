import csv

INPUT_FILE = "Trained With Wugs/maxent_out_no_context.csv"
WEIGHTS_FILE = "weights_no_context.csv"
OUTPUT_FILE = "weighted_output_no_context.csv"

with open(INPUT_FILE, 'rb') as input_file:
	with open(WEIGHTS_FILE, 'rb') as weights:
		with open(OUTPUT_FILE, 'w') as output_file:
			input_reader = csv.reader(input_file, delimiter="\t")
			weights_reader = csv.reader(weights, delimiter="\t")
			writer = csv.writer(output_file, delimiter="\t")

			headers = input_reader.next()
			weights_row = input_reader.next()

			for weight in weights_reader:
				constraint = weight[0].split(" (mu")[0]
				weight_value = weight[1]
				weights_row[headers.index(constraint)] = weight_value
			
			writer.writerow(headers)
			writer.writerow(weights_row)

			for row in input_reader:
				writer.writerow(row)
