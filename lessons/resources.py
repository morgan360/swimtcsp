from import_export import resources, fields
from .models import Group, Product, Category
from import_export.widgets import ForeignKeyWidget
import datetime
from django.utils.text import slugify


class GroupResource(resources.ModelResource):
    category_id = fields.Field(attribute='name')

    class Meta:
        model = Group
        import_id_fields = ('id',)
        fields = ('id', 'category',)


class CategoryResource(resources.ModelResource):
    # we have to name the module_id field in CSV file to program
    # model_id = fields.Field(attribute='program') (Does not WorK)
    lesson = fields.Field(attribute='name')

    class Meta:
        model = Category
        import_id_fields = ('id',)
        fields = ('id', 'program', 'lesson',)


class ProductResource(resources.ModelResource):
    # Note you must change 'category_id' field to 'name' in csv file
    # Crossreference imported fields here
    day_id = fields.Field(attribute='day_of_week')
    # lesson_id = fields.Field(attribute='category')
    time_start = fields.Field(attribute='start_time')
    time_end = fields.Field(attribute='end_time')
    # active = fields.Field(attribute='available')
    lesson_id = fields.Field(attribute='category')
    # category_id = fields.Field(attribute='group')

    class Meta:
        model = Product
        import_id_fields = ('id',)
        fields = ('id', 'day_id', 'category', 'num_places', 'num_weeks', 'price', 'time_start', 'time_end', 'active', 'group')

    # Change the value before you import into model
    def before_import_row(self, row, **kwargs):
        # row['day_id'] = int(row['day_id']) - 1
        row['day_id'] = int(row['day_id'])-1
        row['time_start'] = datetime.datetime.strptime(row['time_start'], '%H:%M:%S').time()
        row['time_end'] = datetime.datetime.strptime(row['time_end'], '%H:%M:%S').time()

        return super().before_import_row(row, **kwargs)
