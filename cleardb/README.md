# cleardb

## How to run

This script is usually called with::

```
   odoo cleardb
```

## Annotations


To add further tables to be cleaned::

```
class A(models.Model):
      _clear_db = True


class A(models.Model):
      _clear_db = " create_date < ONE_YEAR_AGO "

class A(models.Model):
      avalue = fields.Integer(...., cleardb=True)
```

## clear functions

class A(models.Model):

Must start with _clear_db.

```
@api.model
def _clear_db_export_record_sets_from_property(self):
```

# Authors

* Marc Wimmer <marc@itewimmer.de>

