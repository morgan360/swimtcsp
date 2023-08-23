from import_export import resources, fields
from .models import Product, Category
from import_export.widgets import ForeignKeyWidget
import datetime
from django.utils.text import slugify


class CategoryResource(resources.ModelResource):
    # we have to name the module_id field in CSV file to program
    # model_id = fields.Field(attribute='program') (Does not WorK)
    lesson = fields.Field(attribute='name')

    class Meta:
        model = Category
        import_id_fields = ('id',)
        fields = ('id', 'program', 'lesson',)


class ProductResource(resources.ModelResource):
    # category = fields.Field(column_name='category', attribute='category',
    #                         widget=ForeignKeyWidget(Category, 'name'))
    # Crossreference imported fields here
    day_id = fields.Field(attribute='day_of_week')
    # lesson_id = fields.Field(attribute='category')
    time_start = fields.Field(attribute='start_time')
    time_end = fields.Field(attribute='end_time')
    # active = fields.Field(attribute='available')
    lesson_id = fields.Field(attribute='category')
    # Make sure to put the name of the field you are importing here
    class Meta:
        model = Product
        import_id_fields = ('id',)
        fields = ('id', 'day_id', 'category', 'num_places', 'num_weeks', 'price', 'time_start', 'time_end', 'active')

    # Change the value before you import into model
    def before_import_row(self, row, **kwargs):
        # row['day_id'] = int(row['day_id']) - 1
        row['day_id'] = int(row['day_id'])-1
        row['time_start'] = datetime.datetime.strptime(row['time_start'], '%H:%M:%S').time()
        row['time_end'] = datetime.datetime.strptime(row['time_end'], '%H:%M:%S').time()

        return super().before_import_row(row, **kwargs)
