from import_export import resources, fields
from .models import Swimling, User
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget
from django.contrib.auth.models import Group


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
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'mobile_phone', 'other_phone', 'notes', 'groups')
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
            # overriding import_row to ignore errors and skip rows that fail to import
            # without failing the entire import
            import_result = super(ModelResource, self).import_row(
                row, instance_loader, **kwargs
            )

            if import_result.import_type == RowResult.IMPORT_TYPE_ERROR:
                import_result.diff = [
                    row.get(name, '') for name in self.get_field_names()
                ]

                # Add a column with the error message
                import_result.diff.append(
                    "Errors: {}".format(
                        [err.error for err in import_result.errors]
                    )
                )
                # clear errors and mark the record to skip
                import_result.errors = []
                import_result.import_type = RowResult.IMPORT_TYPE_SKIP

            return import_result
