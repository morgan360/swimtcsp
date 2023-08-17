from import_export import resources, fields
from .models import Product, Category
from import_export.widgets import ForeignKeyWidget
import datetime
from django.utils.text import slugify


class ProductResource(resources.ModelResource):
    category = fields.Field(column_name='category', attribute='category',
                            widget=ForeignKeyWidget(Category, 'name'))
    # Crossreference imported fields here
    day_id = fields.Field(attribute='day_of_week')
    time_start = fields.Field(attribute='start_time')
    time_end = fields.Field(attribute='end_time')
    active = fields.Field(attribute='available')

    # Make sure to put the name of the field you are importing here
    class Meta:
        model = Product
        import_id_fields = ('id',)
        fields = ('id', 'category', 'day_id', 'num_places', 'num_weeks',
                  'price', 'time_start', 'time_end', 'active', 'slug')

    # Change the value before you import into model
    def before_import_row(self, row, **kwargs):
        row['time_start'] = datetime.datetime.strptime(row['time_start'],
                                                       '%H:%M:%S').time()
        row['time_end'] = datetime.datetime.strptime(row['time_end'],
                                                     '%H:%M:%S').time()
        row['day_id'] = int(row['day_id']) - 1
        # Generate slug based on category, day_id, time_start, and time_end
        slug_candidate = f"{row['category']}_{row['day_id']}_{row['time_start']}_{row['time_end']}"
        row['slug'] = slugify(
            slug_candidate)  # You need to import slugify from django.utils.text

        # Call the parent before_import_row method to complete the import
        return super().before_import_row(row, **kwargs)
