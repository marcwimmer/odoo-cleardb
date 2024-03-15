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

## central place overview

Just start with prefix.

```
class ClearDB(models.AbstractModel):
    _inherit = 'frameworktools.cleardb'

    _complete_clear_area1 = [
        'bus.bus', 'auditlog.log', 'auditlog.log.line', 'mail_message', 'ir_attachment',
    ]
    _complete_clear_area2 = [
        'bus.bus', 'auditlog.log', 'auditlog.log.line', 'mail_message', 'ir_attachment',
    ]

    _nullify_columns_x1 = [
        'mrp.production:queue_job_id', 'mrp.production:queue_job_id_moved0', 'account.edi.document:attachment_id',
        'mail.channel:message_main_attachment_id', 'product.product:message_main_attachment_id',
        ...

    _constraint_drop_area1 = [
        'mrp.production:mrp_production_queue_job_id_fkey',
        ...
```

# Authors

* Marc Wimmer <marc@itewimmer.de>

