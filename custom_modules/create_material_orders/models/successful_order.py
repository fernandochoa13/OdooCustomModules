from odoo import models, _

class successful_order_wizard(models.TransientModel):
    _name = 'successful.order.wizard'
    _description = 'Successful Order Wizard'

    def continue_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create New Order',
            'res_model': 'create.order.wizard',
            'view_mode': 'form',
            'target': 'current',
            'context': self.env.context,
        }

