import csv
from pathlib import Path

class CSVExporter:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
        
    def export_item(self, item, filename):
        filepath = self.base_path / filename
        
        with filepath.open('a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=item.__class__.FIELDS)
            if filepath.stat().st_size == 0:
                writer.writeheader()
            writer.writerow(item.to_dict())