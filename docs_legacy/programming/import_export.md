---
description: This gives details on importing data from TCSP database,.
---

# import\_export

* can't overwrite an AutoIncrement field
* When Importing dates have to be in the format : '%Y-%m-%d %H:%M:%S'.
* Leave id empty
* You should create a resources.py file in the app directory. This allows you to control import and export.
* import\_id\_fields identifies a unique field which is used during import to decide whether to update or add a record.

```Python
# resources.py
from import_export import resources
from .models import Terms


class TermsResource(resources.ModelResource):
    class Meta:
        model = Terms
        import_id_fields = 'term_id',
        fields = ('term_id', 'start_date', 'end_date', 'rebooking_date',
                  'booking_date', 'assessments_date')
```

[Tutorial](https://www.letscodemore.com/blog/django-import-export-from-basic-to-advance/)

```Python
# admin.py
from django.contrib import admin
from import_export.admin import ImportExportMixin
from .models import Terms
from .resources import TermsResource


class TermsAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = TermsResource
    list_display = ['term_id', 'start_date', 'end_date', 'rebooking_date',
                    'booking_date', 'assessments_date']


admin.site.register(Terms, TermsAdmin)
```

* It looks like that if you specify the primary key that it will overwrite it.
* Foreign Key

```Python
from import_export import resources, fields
from .models import Product, Category
from import_export.widgets import ForeignKeyWidget

class ProductResource(resources.ModelResource):
    category = fields.Field(column_name='category', attribute='category',
                            widget=ForeignKeyWidget(Category, 'name'))
    class Meta:
        model = Product
        import_id_fields = ('id',)
        fields = ('id',  'category',  'day_of_week', 'num_places', 'num_weeks', 'price',)
```

### Student Details

* Delete 000-000-00 (Make blank)
* change guardian\_id to guardian
* use Numners Program and export

### Guardian Details

* vu\_wp\_guardian\_export
* Can use query to get only latest (24/08/2023)

### IMPORT USERS FIRST

```sql
SELECT
   `u1`.`ID` AS `id`,
   `u1`.`user_email` AS `user_email`,
   `u1`.`user_login` AS `username`,
   `m4`.`meta_value` AS `mobile_phone`,
   `m7`.`meta_value` AS `user_phone`,
   `m5`.`meta_value` AS `Role`,
   `m8`.`meta_value` AS `notes`,
   `m9`.`meta_value` AS `other_phone`,
   `m10`.`meta_value` AS `first_name`,
   `m11`.`meta_value` AS `last_name`
FROM `wpmor_users` `u1`
LEFT JOIN `wpmor_usermeta` `m4` ON `m4`.`user_id` = `u1`.`ID` AND `m4`.`meta_key` = 'mobile'
LEFT JOIN `wpmor_usermeta` `m5` ON `m5`.`user_id` = `u1`.`ID` AND `m5`.`meta_key` = 'wpmor_capabilities'
LEFT JOIN `wpmor_usermeta` `m7` ON `m7`.`user_id` = `u1`.`ID` AND `m7`.`meta_key` = 'user_phone'
LEFT JOIN `wpmor_usermeta` `m8` ON `m8`.`user_id` = `u1`.`ID` AND `m8`.`meta_key` = 'description'
LEFT JOIN `wpmor_usermeta` `m9` ON `m9`.`user_id` = `u1`.`ID` AND `m9`.`meta_key` = 'billing_phone'
LEFT JOIN `wpmor_usermeta` `m10` ON `m10`.`user_id` = `u1`.`ID` AND `m10`.`meta_key` = 'first_name'
LEFT JOIN `wpmor_usermeta` `m11` ON `m11`.`user_id` = `u1`.`ID` AND `m11`.`meta_key` = 'last_name';
```

```sql
SELECT `user_id`, `meta_value` 
FROM `wpmor_usermeta` 
WHERE `meta_key` = 'wpmor_capabilities';
```

Export as csv

***

### List of Notebook imports

| Cell                            | Column 2   | Notes                      |
| ------------------------------- | ---------- | -------------------------- |
| Row 1                           | mor\_terms | Fill in blank dates.       |
| Bulk Query                      | Terms, etc | Categories                 |
| public\_swim\_categories.csv    | Data       | Data                       |
| public\_swims.csv               | products   | Data                       |
| public\_swims\_order\_items.csv | Data       | These have to be trasposed |
| Row 6                           | Data       | Data                       |
| Row 7                           | Data       | Data                       |
| Row 8                           | Data       | Data                       |
| Row 9                           | Data       | Data                       |
| Row 10                          | Data       | Data                       |
| Row 11                          | Data       | Data                       |
| Row 12                          | Data       | Data                       |
| Row 13                          | Data       | Data                       |
| Row 14                          | Data       | Data                       |
| Row 15                          | Data       | Data                       |
| Row 16                          | Data       | Data                       |
| Row 17                          | Data       | Data                       |
| Row 18                          | Data       | Data                       |
| Row 19                          | Data       | Data                       |
| Row 20                          | Data       | Data                       |

Upload users in batch files batch1, batch2, batch3, batch 4
