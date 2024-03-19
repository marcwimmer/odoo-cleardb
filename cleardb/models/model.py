from odoo import _, api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError, RedirectWarning, ValidationError

class IrModel(models.Model):
    _inherit = 'ir.model'

    clear_db = fields.Boolean("Clear DB")