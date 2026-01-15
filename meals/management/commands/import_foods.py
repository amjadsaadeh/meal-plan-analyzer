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
            IDX_CARBS = col_to_idx('S')
            IDX_FIBRE = col_to_idx('V')
            IDX_IRON = col_to_idx('EO')
            IDX_SUGAR = col_to_idx('HL')
            IDX_OMEGA3 = col_to_idx('LA')
            IDX_VITC = col_to_idx('DO')
            IDX_MAGNESIUM = col_to_idx('EF')
            IDX_ZINC = col_to_idx('ER')
            IDX_VITB12 = col_to_idx('DK')
            IDX_VITA = col_to_idx('AH')
            IDX_CALCIUM = col_to_idx('EC')
            IDX_VITD = col_to_idx('AW')

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
                carbs = parse_float(row[IDX_CARBS])
                fibre = parse_float(row[IDX_FIBRE])
                iron = parse_float(row[IDX_IRON])
                sugar = parse_float(row[IDX_SUGAR])
                omega3 = parse_float(row[IDX_OMEGA3])
                vitc = parse_float(row[IDX_VITC])
                magnesium = parse_float(row[IDX_MAGNESIUM])
                zinc = parse_float(row[IDX_ZINC])
                vitb12 = parse_float(row[IDX_VITB12])
                vita = parse_float(row[IDX_VITA])
                calcium = parse_float(row[IDX_CALCIUM])
                vitd = parse_float(row[IDX_VITD])

                Food.objects.update_or_create(
                    bls_code=bls_code,
                    defaults={
                        'name': name,
                        'energy_in_kj_per_100g': energy_kj,
                        'energy_in_kcal_per_100g': energy_kcal,
                        'protein_in_g_per_100g': protein,
                        'fat_in_g_per_100g': fat,
                        'carbohydrate_in_g_per_100g': carbs,
                        'fibre_in_g_per_100g': fibre,
                        'iron_in_mg_per_100g': iron,
                        'sugar_in_g_per_100g': sugar,
                        'omega3_in_g_per_100g': omega3,
                        'vitc_in_mg_per_100g': vitc,
                        'magnesium_in_mg_per_100g': magnesium,
                        'zinc_in_mg_per_100g': zinc,
                        'vitb12_in_mug_per_100g': vitb12,
                        'vita_in_mug_per_100g': vita,
                        'calcium_in_mg_per_100g': calcium,
                        'vitd_in_mug_per_100g': vitd,
                    }
                )
                count += 1
                
            self.stdout.write(self.style.SUCCESS(f'Successfully imported {count} foods.'))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred: {str(e)}'))
