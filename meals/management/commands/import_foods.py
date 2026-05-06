import os
import shutil
import tempfile
import urllib.request
import urllib.error
import zipfile
from contextlib import contextmanager

import openpyxl
from django.core.management.base import BaseCommand
from tqdm import tqdm

from meals.models import Food


class Command(BaseCommand):
    help = "Import food data from an Excel file (.xlsx), ZIP file, or URL"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path", type=str, help="Path to xlsx/zip file or URL (http/https)"
        )

    def _find_xlsx_in_zip(self, zip_path: str, extract_dir: str) -> str | None:
        with zipfile.ZipFile(zip_path, "r") as zf:
            xlsx_files = [
                f
                for f in zf.namelist()
                if f.endswith(".xlsx") and "Daten" in os.path.basename(f)
            ]
            if not xlsx_files:
                all_xlsx = [f for f in zf.namelist() if f.endswith(".xlsx")]
                if all_xlsx:
                    self.stdout.write(
                        self.style.WARNING(
                            f'No xlsx file with "Daten" in name found. Available: {all_xlsx}'
                        )
                    )
                return None
            if len(xlsx_files) > 1:
                self.stdout.write(
                    self.style.WARNING(
                        f'Multiple "Daten" xlsx files found: {xlsx_files}'
                    )
                )
            target = xlsx_files[0]
            zf.extract(target, extract_dir)
            return os.path.join(extract_dir, target)

    @contextmanager
    def _get_xlsx_path(self, source: str):
        is_url = source.startswith("http://") or source.startswith("https://")
        temp_download = None
        temp_extract_dir = None

        try:
            file_path = source

            if is_url:
                suffix = ".zip" if source.lower().endswith(".zip") else ".xlsx"
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tf:
                    temp_download = tf.name

                try:
                    self.stdout.write(f"Downloading from: {source}")
                    urllib.request.urlretrieve(source, temp_download)
                    self.stdout.write(self.style.SUCCESS("Download complete."))
                except urllib.error.URLError as e:
                    os.unlink(temp_download)
                    self.stderr.write(self.style.ERROR(f"Failed to download file: {e}"))
                    raise
                except Exception as e:
                    if os.path.exists(temp_download):
                        os.unlink(temp_download)
                    self.stderr.write(self.style.ERROR(f"Download error: {e}"))
                    raise

                file_path = temp_download

            is_zip = file_path.lower().endswith(".zip")

            if is_zip:
                temp_extract_dir = tempfile.mkdtemp()
                self.stdout.write("Extracting ZIP file...")
                xlsx_path = self._find_xlsx_in_zip(file_path, temp_extract_dir)
                if not xlsx_path:
                    raise ValueError(
                        'No xlsx file with "Daten" in name found in ZIP archive.'
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Found data file: {os.path.basename(xlsx_path)}"
                    )
                )
                yield xlsx_path
            else:
                yield file_path

        finally:
            if temp_extract_dir and os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            if temp_download and os.path.exists(temp_download):
                os.unlink(temp_download)

    def handle(self, *args, **options):
        source = options["file_path"]

        try:
            with self._get_xlsx_path(source) as xlsx_path:
                try:
                    workbook = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
                except FileNotFoundError:
                    self.stderr.write(self.style.ERROR(f"File not found: {xlsx_path}"))
                    return
                except openpyxl.utils.exceptions.InvalidFileException:
                    self.stderr.write(
                        self.style.ERROR(f"Invalid file format. Expected .xlsx file.")
                    )
                    return
                except Exception as e:
                    self.stderr.write(
                        self.style.ERROR(f"Failed to parse Excel file: {str(e)}")
                    )
                    return

                sheet = workbook.active

                self.stdout.write(self.style.SUCCESS(f"Opened file"))

                def col_to_idx(col_str):
                    exp = 0
                    idx = 0
                    for char in reversed(col_str.upper()):
                        idx += (ord(char) - ord("A") + 1) * (26**exp)
                        exp += 1
                    return idx - 1

                IDX_BLS = col_to_idx("A")
                IDX_NAME = col_to_idx("B")
                IDX_KJ = col_to_idx("D")
                IDX_KCAL = col_to_idx("G")
                IDX_WATER = col_to_idx("J")
                IDX_PROTEIN = col_to_idx("M")
                IDX_FAT = col_to_idx("P")
                IDX_CARBS = col_to_idx("S")
                IDX_FIBRE = col_to_idx("V")
                IDX_IRON = col_to_idx("EO")
                IDX_SUGAR = col_to_idx("HL")
                IDX_OMEGA3 = col_to_idx("LA")
                IDX_VITC = col_to_idx("DN")
                IDX_MAGNESIUM = col_to_idx("EF")
                IDX_ZINC = col_to_idx("ER")
                IDX_VITB12 = col_to_idx("DK")
                IDX_VITA = col_to_idx("AH")
                IDX_CALCIUM = col_to_idx("EC")
                IDX_VITD = col_to_idx("AW")
                IDX_VITB1 = col_to_idx("CG")
                IDX_VITB2 = col_to_idx("CJ")
                IDX_VITB3 = col_to_idx("CM")
                IDX_VITB5 = col_to_idx("CS")
                IDX_VITB6 = col_to_idx("CV")
                IDX_BIOTIN = col_to_idx("CY")
                IDX_IODINE = col_to_idx("EU")
                IDX_COPPER = col_to_idx("EX")
                IDX_MANGANESE = col_to_idx("FA")
                IDX_MOLYBDENUM = col_to_idx("FJ")

                count = 0

                for row_idx, row in enumerate(
                    tqdm(sheet.iter_rows(min_row=2, values_only=True), desc="Importing foods", unit="item"), start=2
                ):
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
                    water = parse_float(row[IDX_WATER])
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
                    vitb1 = parse_float(row[IDX_VITB1])
                    vitb2 = parse_float(row[IDX_VITB2])
                    vitb3 = parse_float(row[IDX_VITB3])
                    vitb5 = parse_float(row[IDX_VITB5])
                    vitb6 = parse_float(row[IDX_VITB6])
                    biotin = parse_float(row[IDX_BIOTIN])
                    iodine = parse_float(row[IDX_IODINE])
                    copper = parse_float(row[IDX_COPPER])
                    manganese = parse_float(row[IDX_MANGANESE])
                    molybdenum = parse_float(row[IDX_MOLYBDENUM])

                    Food.objects.update_or_create(
                        bls_code=bls_code,
                        defaults={
                            "name": name,
                            "energy_in_kj_per_100g": energy_kj,
                            "energy_in_kcal_per_100g": energy_kcal,
                            "water_in_g_per_100g": water,
                            "protein_in_g_per_100g": protein,
                            "fat_in_g_per_100g": fat,
                            "carbohydrate_in_g_per_100g": carbs,
                            "fibre_in_g_per_100g": fibre,
                            "iron_in_mg_per_100g": iron,
                            "sugar_in_g_per_100g": sugar,
                            "omega3_in_g_per_100g": omega3,
                            "vitc_in_mg_per_100g": vitc,
                            "magnesium_in_mg_per_100g": magnesium,
                            "zinc_in_mg_per_100g": zinc,
                            "vitb12_in_mug_per_100g": vitb12,
                            "vita_in_mug_per_100g": vita,
                            "calcium_in_mg_per_100g": calcium,
                            "vitd_in_mug_per_100g": vitd,
                            "vitb1_in_mg_per_100g": vitb1,
                            "vitb2_in_mg_per_100g": vitb2,
                            "vitb3_in_mg_per_100g": vitb3,
                            "vitb5_in_mg_per_100g": vitb5,
                            "vitb6_in_mug_per_100g": vitb6,
                            "biotin_in_mug_per_100g": biotin,
                            "iodine_in_mug_per_100g": iodine,
                            "copper_in_mug_per_100g": copper,
                            "manganese_in_mug_per_100g": manganese,
                            "molybdenum_in_mug_per_100g": molybdenum,
                            "data_source": "bls",
                        },
                    )
                    count += 1

                self.stdout.write(
                    self.style.SUCCESS(f"Successfully imported {count} foods.")
                )

        except ValueError as e:
            self.stderr.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An error occurred: {str(e)}"))
