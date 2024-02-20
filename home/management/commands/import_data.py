from django.core.management.base import BaseCommand
from tablib import Dataset
from lessons.resources import ProgramResource, CategoryResource, ProductResource  # Adjust import paths as needed


class Command(BaseCommand):
    help = 'Import data into Program, Category, and Product models'

    def handle(self, *args, **kwargs):
        # Hard-coded CSV file paths
        program_csv_path = 'import_csv/programs.csv'
        category_csv_path = 'import_csv/categories.csv'
        product_csv_path = 'import_csv/lessons.csv'

        # Import Program data
        self.import_data(ProgramResource, program_csv_path, 'Program')

        # Import Category data
        self.import_data(CategoryResource, category_csv_path, 'Category')

        # Import Product data
        self.import_data(ProductResource, product_csv_path, 'Product')

    def import_data(self, resource_class, csv_file_path, model_name):
        """Utility method to import data from a CSV file using a specified resource class."""
        with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
            dataset = Dataset().load(csv_file.read(), format='csv')
        resource = resource_class()
        result = resource.import_data(dataset, raise_errors=True)
        if not result.has_errors():
            self.stdout.write(self.style.SUCCESS(f'Successfully imported data into {model_name}'))
        else:
            self.stdout.write(self.style.ERROR(f'Errors occurred while importing data into {model_name}'))
