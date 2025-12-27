from odoo import api, models, fields


class pms_windows(models.Model):
    _name = "pms.windows"
    _description = "Types of windows"

    # === General Property Description === #
    name = fields.Char(string="Name of type windows")
