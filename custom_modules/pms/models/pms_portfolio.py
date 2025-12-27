from odoo import api, models, fields


class pms_portfolio(models.Model):
    _name = 'pms.portfolio'
    _description = 'PMS Portfolio'    
    
    arv = fields.Float(string="ARV")
    color = fields.Char(string="Color")
    property_address = fields.One2many('pms.property', 'portfolio', string="Property Address")
    name = fields.Char(string='Portfolio Name')
    
    _sql_constraints = [
        ('ref_unique', 'unique(color)', 'Color must be unique.'),
    ]