from odoo import models, fields, api

class product_price_wizard(models.TransientModel):
    _name = 'product.price.wizard'
    _description = 'Product Price Wizard'

    message = fields.Text(default=lambda self: self.env.context.get('price_id', False), store=False, readonly=True, string="Message")
    
    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
    def ignore_continue(self):
        ctx = self.env.context.get('price_ignore_id')
        self.env['account.move'].browse(ctx).action_post()
        return {'type': 'ir.actions.act_window_close'}
    
    