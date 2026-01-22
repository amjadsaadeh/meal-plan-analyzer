import pytest
import os
import openpyxl
from django.core.management import call_command
from meals.models import Food

@pytest.mark.django_db
def test_food_import_from_xlsx():
    # Path to the generated test file
    test_file_path = "/home/orchid/projects/rsos-meal-planning-app/tests/data/test_foods.xlsx"
    
    # Ensure file exists
    assert os.path.exists(test_file_path), f"Test file not found at {test_file_path}"
    
    # Clear existing foods to ensure a clean state
    Food.objects.all().delete()
    
    # Run the import command
    call_command('import_foods', test_file_path)
    
    # Check if 100 foods were imported
    assert Food.objects.count() == 100
    
    # Verification of a specific entry
    # Let's read the first row from the xlsx (excluding header)
    wb = openpyxl.load_workbook(test_file_path, data_only=True)
    ws = wb.active
    first_code = ws['A2'].value
    first_name = ws['B2'].value
    first_kcal = float(ws['G2'].value)
    
    food = Food.objects.get(bls_code=first_code)
    assert food.name == first_name
    assert pytest.approx(food.energy_in_kcal_per_100g) == first_kcal

@pytest.mark.django_db
def test_food_import_update_existing():
    # Test updating existing records
    test_file_path = "/home/orchid/projects/rsos-meal-planning-app/tests/data/test_foods.xlsx"
    
    # Create a food that already exists but with different name
    wb = openpyxl.load_workbook(test_file_path, data_only=True)
    ws = wb.active
    code = ws['A2'].value
    
    Food.objects.create(
        bls_code=code,
        name="Old Name",
        energy_in_kj_per_100g=0,
        energy_in_kcal_per_100g=0
    )
    
    # Run import
    call_command('import_foods', test_file_path)
    
    # Check if name was updated
    food = Food.objects.get(bls_code=code)
    assert food.name == ws['B2'].value
    assert food.energy_in_kcal_per_100g > 0
