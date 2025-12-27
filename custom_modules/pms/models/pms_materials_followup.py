from odoo import models, fields, api

class material_order_follow_up(models.Model):
    _name = 'material.order.follow.up'
    _description = 'Material Order Follow Up'
    
    material_id = fields.Many2one('pms.materials', string='Material Order')
    comment = fields.Text(string='Comment')
    date = fields.Datetime(string='Date', default=fields.Datetime.now())


