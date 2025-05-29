import json
import csv
import os

def json_to_csv(json_files, csv_filename="Json2Csvoutput.csv"):
    """
    Reads JSON files from a list, extracts specified fields, and writes to a CSV file.

    Args:
        json_files (list): A list of JSON file paths.
        csv_filename (str): The name of the output CSV file.
    """

    data = []
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
                if isinstance(json_data, list):
                    data.extend(json_data)
                else:
                    data.append(json_data)
        except FileNotFoundError:
            print(f"File not found: {file_path}")
        except json.JSONDecodeError:
            print(f"Invalid JSON in file: {file_path}")

    if not data:
        print("No valid JSON data found.")
        return

    fieldnames = ["title", "price", "address", "details", "builder", "link"]
    max_promotions = 0

    for item in data:
        if "promotions" in item and isinstance(item["promotions"], list):
            max_promotions = max(max_promotions, len(item["promotions"]))

    for i in range(1, max_promotions + 1):
        fieldnames.extend([f"promo_title{i}", f"promo_content{i}"])

    with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for item in data:
            row = {field: item.get(field, "") for field in ["title", "price", "address", "details", "builder", "link"]}

            if "promotions" in item and isinstance(item["promotions"], list):
                for i, promo in enumerate(item["promotions"]):
                    row[f"promo_title{i + 1}"] = promo.get("promo_title", "")
                    row[f"promo_content{i + 1}"] = promo.get("promo_content", "")

            writer.writerow(row)

# Example usage:
json_files = [
    "1getHotDealProperties_output_Apex.json",
    "2getHotDealProperties_output_Cary.json",
    "3getHotDealProperties_output_Clayton.json",
    "4getHotDealProperties_output_Durham.json",
    "5getHotDealProperties_output_FuquayVarina.json",
    "6getHotDealProperties_output_Garner.json",
    "7getHotDealProperties_output_HolySprings.json",
    "8getHotDealProperties_output_Raleigh.json",
]

# Create example json files for testing.
# example_data = [
#     {
#         "title": "Ashford | Wake Forest, NC | Wake Forest, NC",
#         "price": "From $487,999",
#         "address": "Ashford | Wake Forest, NC",
#         "details": "4 Br | 2.5 Ba | 2 Gr | 2,700 sq ft",
#         "builder": "Taylor Morrison",
#         "link": "https://www.newhomesource.com/plan/ashford-taylor-morrison-wake-forest-nc/2523216",
#         "promotions": [{"promo_title": "Reduced rates are here. Save Now!", "promo_content": "Reduced rates just dropped: Conventional 30-year fixed rate 5.49% / 5.57% APR*"}]
#     },
#     {
#         "title": "964 Myers Point Drive. Morrisville, NC 27560 ",
#         "price": "From $799,990",
#         "address": "964 Myers Point Drive. Morrisville, NC 27560",
#         "details": "4 Br | 3.5 Ba | 2 Gr | 3,382 sq ft",
#         "builder": "Baker Residential",
#         "link": "https://www.newhomesource.com/specdetail/964-myers-point-drive-morrisville-nc-27560/2833981",
#         "promotions": []
#     },
#     {
#         "title": "2425 Englemann Drive. Apex, NC 27502 ",
#         "price": "From $641,320",
#         "address": "2425 Englemann Drive. Apex, NC 27502",
#         "details": "4 Br | 3.5 Ba | 2 Gr | 2,339 sq ft",
#         "builder": "M/I Homes",
#         "link": "https://www.newhomesource.com/specdetail/2425-englemann-drive-apex-nc-27502/2883536",
#         "promotions": [{"promo_title": "Built for You", "promo_content": "M/I Homes is built for you, offering savings, financial flexibility, and lower payments. For a limited time, enjoy up to $25,000 in paid closing costs on select Quick Move-In homes."}]
#     },
#     {
#         "title": "2464 Field Poppy Drive. Apex, NC 27502 ",
#         "price": "From $679,010",
#         "address": "2464 Field Poppy Drive. Apex, NC 27502",
#         "details": "4 Br | 3.5 Ba | 2 Gr | 2,339 sq ft",
#         "builder": "M/I Homes",
#         "link": "https://www.newhomesource.com/specdetail/2464-field-poppy-drive-apex-nc-27502/2821315",
#         "promotions": [{"promo_title": "Built for You", "promo_content": "M/I Homes is built for you, offering savings, financial flexibility, and lower payments. For a limited time, enjoy up to $25,000 in paid closing costs on select Quick Move-In homes."}, {"promo_title": "Second Promo", "promo_content": "Second Promo Content"}]
#     },
#     {
#         "title": "2391 Englemann Drive. Apex, NC 27502 ",
#         "price": "From $692,940",
#         "address": "2391 Englemann Drive. Apex, NC 27502",
#         "details": "4 Br | 3.5 Ba | 2 Gr | 2,638 sq ft",
#         "builder": "M/I Homes",
#         "link": "https://www.newhomesource.com/specdetail/2391-englemann-drive-apex-nc-27502/2850904",
#         "promotions": [{"promo_title": "Built for You", "promo_content": "M/I Homes is built for you, offering savings, financial flexibility, and lower payments. For a limited time, enjoy up to $25,000 in paid closing costs on select Quick Move-In homes."}]
#     }
# ]

# for i, data in enumerate(example_data):
#     with open(f"data{i+1}.json", 'w') as f:
#         json.dump(data, f, indent=4)

json_to_csv(json_files)