import os
import json
import csv

def create_patterncsv(json_dir, output_csv):
    # Define the classes
    classes = ['front_mac', 'mid_band', 'rear_mac', 'reduced_front', 'reduced_mid', 'reduced_rear', 'marginal_line', 'filled', 'immaculate', 'non_specimen']

    # Prepare the header for the CSV file
    csv_header = ['spec_filename', 'full_id'] + classes

    # Load existing CSV data if the file exists
    existing_data = {}
    if os.path.exists(output_csv):
        with open(output_csv, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                existing_data[row['spec_filename']] = row

    # Prepare the data structure to hold the new CSV data
    csv_data = []

    # Iterate over each JSON file in the directory and subdirectories
    for root, _, files in os.walk(json_dir):
        for json_file in files:
            if json_file.endswith('.json'):
                spec_filename = json_file.replace('.json', '.jpg')
                full_id = json_file.replace('.json', '')
                
                # Check if the data is already in the CSV
                if spec_filename in existing_data:
                    print(f"Data for '{spec_filename}' already in CSV, skipping...")
                    continue

                # Load the JSON file
                json_path = os.path.join(root, json_file)
                with open(json_path, 'r') as f:
                    data = json.load(f)

                # Initialize the row with 0s for all classes
                row = {class_name: 0 for class_name in classes}
                row['spec_filename'] = spec_filename
                row['full_id'] = full_id

                # Check which classes are present in the predictions
                predictions = data.get('predictions', [{}])[0].get('predictions', {})
                for class_name in classes:
                    if class_name in predictions:
                        row[class_name] = predictions[class_name]['confidence']

                # Append the row to the csv_data
                csv_data.append(row)

    # Write the new data to CSV, appending to existing data
    with open(output_csv, 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_header)
        if not existing_data:  # Write header only if the CSV file didn't exist
            writer.writeheader()
        writer.writerows(csv_data)

    print(f"CSV file '{output_csv}' updated successfully.")


