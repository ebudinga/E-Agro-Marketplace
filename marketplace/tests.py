from django.test import TestCase
from marketplace.models import Category

# Create some categories
Category.objects.create(name="Vegetables")
Category.objects.create(name="Fruits")
Category.objects.create(name="Grains")
Category.objects.create(name="Dairy")
