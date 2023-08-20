from import_export import resources, fields
from .models import PublicSwimCategory, PublicSwimProduct
from import_export.widgets import ForeignKeyWidget
import datetime
from django.utils.text import slugify


class PublicSwimCategoryResource(resources.ModelResource):
    # Crossreference imported fields here
    event = fields.Field(attribute='name')

    class Meta:
        model = PublicSwimCategory
        import_id_fields = ('id',)
        fields = ('id', 'event', 'slug')

    # Change the value before you import into model
    def before_import_row(self, row, **kwargs):
        # Generate slug
        slug_candidate = row['event']
        row['slug'] = slugify(slug_candidate)

        # Call the parent before_import_row method to complete the import
        return super().before_import_row(row, **kwargs)


class PublicSwimProductResource(resources.ModelResource):
    day_id = fields.Field(attribute='day_of_week')
    time_start = fields.Field(attribute='start_time')
    time_end = fields.Field(attribute='end_time')
    active = fields.Field(attribute='available')
    # event_id = fields.Field(attribute='category')
    event_id = fields.Field(column_name='event_id', attribute='category',
                            widget=ForeignKeyWidget(PublicSwimCategory, 'id'))

    class Meta:
        model = PublicSwimProduct
        import_id_fields = ('id',)
        fields = ('id', 'event_id', 'day_id', 'num_places', 'time_start', 'time_end', 'active')

    def before_import_row(self, row, **kwargs):
        row['day_id'] = int(row['day_id']) - 1

        row['time_start'] = datetime.datetime.strptime(row['time_start'], '%H:%M:%S').time()
        row['time_end'] = datetime.datetime.strptime(row['time_end'], '%H:%M:%S').time()

        return super().before_import_row(row, **kwargs)
