from odoo import api, models, fields


class pms_roof(models.Model):
    _name = "pms.roof"
    _description = "Types of roofs"

    # === General Property Description === #
    name = fields.Char(string="Name of type roof")
    
        
