import csv
import os

input_file = '/home/venu/Proposals/Jarvis/automations/pinterest/data.csv'
output_file = '/home/venu/Proposals/Jarvis/automations/pinterest/data.csv.tmp'

with open(input_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    rows = list(reader)

filtered_rows = []
removed = 0
for row in rows:
    if row.get('Pin Type', '').strip().lower() == 'content' or not row.get('Image URL', '').strip():
        removed += 1
    else:
        filtered_rows.append(row)

with open(output_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(filtered_rows)

os.replace(output_file, input_file)

print(f'Removed {removed} text-only content pins. Kept {len(filtered_rows)} high-quality Amazon image pins.')
