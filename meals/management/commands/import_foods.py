import openpyxl
from django.core.management.base import BaseCommand
from meals.models import Food

class Command(BaseCommand):
    help = 'Import food data from an Excel file (.xlsx)'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the xlsx file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        
        try:
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook.active
            
            self.stdout.write(self.style.SUCCESS(f'Opened file: {file_path}'))
            
            count = 0
            # Assuming row 1 is headers, start from row 2
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                # Col A: bls_code (index 0)
                # Col B: name (index 1)
                # Col D: energy_in_kj_per_100g (index 3)
                # Col G: energy_in_kcal_per_100g (index 6)
                
                bls_code = str(row[0]).strip() if row[0] else None
                name = str(row[1]).strip() if row[1] else None
                energy_kj = row[3]
                energy_kcal = row[6]

                if not bls_code or not name:
                    self.stdout.write(self.style.WARNING(f'Skipping row {row_idx}: Missing bls_code or name'))
                    continue

                try:
                    # Clean/Format values if necessary
                    energy_kj = float(energy_kj) if energy_kj is not None else 0.0
                    energy_kcal = float(energy_kcal) if energy_kcal is not None else 0.0
                except (ValueError, TypeError):
                    self.stdout.write(self.style.WARNING(f'Row {row_idx}: Invalid energy values, setting to 0.0'))
                    energy_kj = 0.0
                    energy_kcal = 0.0

                Food.objects.update_or_create(
                    bls_code=bls_code,
                    defaults={
                        'name': name,
                        'energy_in_kj_per_100g': energy_kj,
                        'energy_in_kcal_per_100g': energy_kcal,
                    }
                )
                count += 1
                
                if count % 100 == 0:
                    self.stdout.write(f'Imported {count} items...')

            self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} foods.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred: {str(e)}'))
