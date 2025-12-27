from odoo import models, fields

class budget_model(models.Model):
    _name = 'budget.model'
    _description = 'Budget Model'
    _rec_name = 'activity'
    
    id = fields.Integer(readonly=True)
    house_model = fields.Many2one('pms.housemodels', string='House Model', required=True)
    product_model = fields.Many2one('product.template', string='Product Model', required=True)
    amount = fields.Float(string='Amount', required=True)
    supplier = fields.Many2one('res.partner', string='Supplier', required=True)
    activity = fields.Many2one('pms.activity.costs', string='Activity')
    county = fields.Many2one('pms.county', string='County')
    city = fields.Many2one('pms.cities', string='City')