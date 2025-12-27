from odoo import api, models, fields
from odoo.exceptions import ValidationError

class product_subproduct(models.Model):
    _name = "product.subproduct"
    _description = "Subproducts"

    name = fields.Char(required=True, string="Subproduct")
    subproduct_id = fields.Many2one('daily.property.report', string='Subproduct ID*') # Unknown comodel_name 'daily.property.report'.
    subproduct_idd = fields.Many2one('pms.property.report', string='Subproduct ID')

class product_template(models.Model):
    _inherit = "product.template"

    max_price = fields.Float(string="Max Price Range")    
    
