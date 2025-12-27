from odoo import api, models, fields


class pms_floors(models.Model):
    _name = "pms.floors"
    _description = "Types of floors"

    # === General Property Description === #
    name = fields.Char(string="Name of type floors")
