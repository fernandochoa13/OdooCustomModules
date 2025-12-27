from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

class pms_provider_config(models.Model):
    _name = "pms.provider.config"
    _description = "Table for Property Provider Configuration"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    partner_id = fields.Many2one("res.partner", string="Provider", required=True)
    company_id = fields.Many2one("res.company", string="Company", required=True)

    