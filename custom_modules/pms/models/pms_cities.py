from odoo import api, models, fields
from odoo.exceptions import ValidationError



# test

class pms_cities(models.Model):
    _name = "pms.cities"
    _description = "Cities for properties"

    name = fields.Char(required=True, string="City")
    county = fields.Many2one("pms.county")
    state = fields.Many2one("res.country.state")
    country = fields.Many2one("res.country")
