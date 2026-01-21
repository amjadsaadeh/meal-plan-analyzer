import json
import random
import uuid
from faker import Faker

fake = Faker()

def generate_food_fixtures(count=100):
    foods = []
    for i in range(count):
        food = {
            "model": "meals.food",
            "pk": i + 1,
            "fields": {
                "bls_code": f"T{fake.unique.bothify(text='??#######')}",
                "name": fake.word().capitalize() + " " + fake.word(),
                "energy_in_kj_per_100g": round(random.uniform(50, 2000), 1),
                "energy_in_kcal_per_100g": round(random.uniform(10, 500), 1),
                "protein_in_g_per_100g": round(random.uniform(0, 30), 1),
                "fat_in_g_per_100g": round(random.uniform(0, 50), 1),
                "carbohydrate_in_g_per_100g": round(random.uniform(0, 80), 1),
                "fibre_in_g_per_100g": round(random.uniform(0, 15), 1),
                "iron_in_mg_per_100g": round(random.uniform(0, 15), 1),
                "sugar_in_g_per_100g": round(random.uniform(0, 50), 1),
                "omega3_in_g_per_100g": round(random.uniform(0, 5), 2),
                "vitc_in_mg_per_100g": round(random.uniform(0, 100), 1),
                "magnesium_in_mg_per_100g": round(random.uniform(0, 400), 1),
                "zinc_in_mg_per_100g": round(random.uniform(0, 15), 1),
                "vitb12_in_mug_per_100g": round(random.uniform(0, 5), 2),
                "vita_in_mug_per_100g": round(random.uniform(0, 1000), 1),
                "calcium_in_mg_per_100g": round(random.uniform(0, 1000), 1),
                "vitd_in_mug_per_100g": round(random.uniform(0, 10), 2)
            }
        }
        foods.append(food)
    
    return foods

if __name__ == "__main__":
    fixtures = generate_food_fixtures(100)
    with open("tests/data/food_fixtures.json", "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=4, ensure_ascii=False)
    print(f"Generated 100 food fixtures in tests/data/food_fixtures.json")
