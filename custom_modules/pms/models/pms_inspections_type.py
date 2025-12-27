from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date


class pms_inspections_type(models.Model):
    _name = "pms.inspections.type"
    _description = "Table for Inspections Type"

    name = fields.Char(string="Inspection Type") 
    county = fields.Many2one('pms.county', string='County')
    add_to_report = fields.Boolean(string="Add to Report", default=False, required=False)