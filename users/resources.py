from import_export import resources, fields
from .models import Swimling, User
from import_export.widgets import ForeignKeyWidget



class UserResource(resources.ModelResource):
    category_id = fields.Field(attribute='name')

    class Meta:
        model = User
        import_id_fields = ('id',)
        fields = ('id', 'first_name', 'last_name', 'email', 'mobile_phone', 'notes', 'groups', 'sco_role_num')

        def before_import(self, dataset, using_transactions, dry_run, **kwargs):
            # Map the group names to Group objects
            group_names = dataset['groups'].split(',') if 'groups' in dataset else []
            groups = Group.objects.filter(name__in=group_names)
            dataset.append_col(groups, header="groups")

        def save_instance(self, instance, using_transactions=True, dry_run=False):
            # Save the instance with groups
            super().save_instance(instance, using_transactions, dry_run)
            if 'groups' in self.fields and hasattr(instance, 'groups'):
                instance.groups.set(self.fields['groups'].clean())


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

