import pytest
import weasyprint
from django.template.loader import render_to_string
from django.contrib.staticfiles import finders
from tests.frontend.factories import MealPlanFactory

@pytest.mark.django_db
def test_pdf():
    from meals.views import get_meal_plan_context
    
    # Create a plan in the test database
    plan = MealPlanFactory(name="Test Plan")
    
    context = get_meal_plan_context(plan.id)
    logo_disk_path = finders.find('meals/img/logo.png')
    if logo_disk_path:
        context['logo_path'] = f"file://{logo_disk_path}"
        print(f"Using logo path: {context['logo_path']}")
    else:
        print("Logo not found via finders!")
        
    html_string = render_to_string('meals/mealplan_pdf.html.j2', context)
    
    # Check if logo path is in HTML
    if context.get('logo_path') in html_string:
        print("Logo path found in HTML string.")
    else:
        print("Logo path NOT found in HTML string!")
        
    html = weasyprint.HTML(string=html_string, base_url="http://localhost:8001")
    pdf = html.write_pdf()
    
    assert len(pdf) > 0
    print(f"PDF generated: {len(pdf)} bytes")
