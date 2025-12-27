from odoo import api, models, fields
from odoo.exceptions import ValidationError

class pms_cities(models.Model):
    _name = "pms.county"
    _description = "County for properties"

    name = fields.Char(required=True, string="City")
    state = fields.Many2one('res.country.state', required=True, string='Federal States')
    has_association = fields.Boolean(string="Has an association?", help="indicate if city has an association")