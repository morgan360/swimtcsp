from import_export import resources, fields
from .models import Swimling, User
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from django.contrib.auth.models import Group
from import_export.results import RowResult


class GroupResource(resources.ModelResource):
    class Meta:
        model = Group


class UserResource(resources.ModelResource):
    groups = fields.Field(
        column_name='groups',
        attribute='groups',
        widget=ManyToManyWidget(Group, field='name')
    )

    class Meta:
        model = User
        fields = (
        'id', 'email', 'username', 'first_name', 'last_name', 'mobile_phone', 'other_phone', 'notes', 'groups')
        import_id_fields = ('id',)  # Assuming 'id' is used to identify unique records for update

    def before_import_row(self, row, **kwargs):
        if 'groups' in row:
            group_names = [name.strip() for name in row['groups'].split(',') if name.strip()]
            for name in group_names:
                Group.objects.get_or_create(name=name)


class SwimlingResource(resources.ModelResource):
    class Meta:
        model = Swimling
        import_id_fields = ('id',)
        fields = ('id', 'first_name', 'last_name', 'guardian', 'notes', 'dob')

    def import_row(self, row, instance_loader, **kwargs):
        import_result = super().import_row(row, instance_loader, **kwargs)

        if import_result.import_type == RowResult.IMPORT_TYPE_ERROR:
            # Manually construct field names list
            field_names = self._meta.fields

            # Log the row values and the errors
            import_result.diff = [row.get(name, '') for name in field_names]
            import_result.diff.append("Errors: {}".format(", ".join([str(err.error) for err in import_result.errors])))

            # Clear errors and mark the record to skip
            import_result.errors = []
            import_result.import_type = RowResult.IMPORT_TYPE_SKIP

        return import_result