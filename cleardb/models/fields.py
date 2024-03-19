from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class OdooFields(models.Model):
    _inherit = "ir.model.fields"

    clear_db = fields.Boolean("Clear DB")
