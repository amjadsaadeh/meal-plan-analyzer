import openpyxl
from tqdm import tqdm
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
            
            def col_to_idx(col_str):
                """Converts Excel column letter (e.g., 'A', 'EO', 'HL') to 0-based index."""
                exp = 0
                idx = 0
                for char in reversed(col_str.upper()):
                    idx += (ord(char) - ord('A') + 1) * (26 ** exp)
                    exp += 1
                return idx - 1

            # Mappings
            IDX_BLS = col_to_idx('A')
            IDX_NAME = col_to_idx('B')
            IDX_KJ = col_to_idx('D')
            IDX_KCAL = col_to_idx('G')
            IDX_PROTEIN = col_to_idx('M')
            IDX_FAT = col_to_idx('P')
            IDX_FIBRE = col_to_idx('V')
            IDX_IRON = col_to_idx('EO')
            IDX_SUGAR = col_to_idx('HL')

            count = 0
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            
            for row_idx, row in enumerate(tqdm(rows, desc="Importing foods", unit="item"), start=2):
                bls_code = str(row[IDX_BLS]).strip() if row[IDX_BLS] else None
                name = str(row[IDX_NAME]).strip() if row[IDX_NAME] else None
                
                if not bls_code or not name:
                    continue

                def parse_float(val):
                    try:
                        return float(val) if val is not None else 0.0
                    except (ValueError, TypeError):
                        return 0.0

                energy_kj = parse_float(row[IDX_KJ])
                energy_kcal = parse_float(row[IDX_KCAL])
                protein = parse_float(row[IDX_PROTEIN])
                fat = parse_float(row[IDX_FAT])
                fibre = parse_float(row[IDX_FIBRE])
                iron = parse_float(row[IDX_IRON])
                sugar = parse_float(row[IDX_SUGAR])

                Food.objects.update_or_create(
                    bls_code=bls_code,
                    defaults={
                        'name': name,
                        'energy_in_kj_per_100g': energy_kj,
                        'energy_in_kcal_per_100g': energy_kcal,
                        'protein_in_g_per_100g': protein,
                        'fat_in_g_per_100g': fat,
                        'fibre_in_g_per_100g': fibre,
                        'iron_in_mg_per_100g': iron,
                        'sugar_in_g_per_100g': sugar,
                    }
                )
                count += 1
                
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} foods.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred: {str(e)}'))
