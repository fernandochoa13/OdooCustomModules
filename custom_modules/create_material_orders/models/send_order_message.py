from odoo import fields, models,  _

class send_order_message_wizard(models.TransientModel):
    _name = 'send.order.message.wizard'
    _description = 'Verify Order Report Wizard'

    message = fields.Text('Message', required=True)
    
    def send_message(self):
        active_id = self._context.get('active_id')
        model_name = self._context.get('model')
        
        if not model_name:
            raise ValueError("Model name is missing from the context")
        
        model = self.env[model_name] #Dynamically get the model
        record = model.browse(active_id)
        record.sudo().message_post(body=self.message)
        return True

    # def send_message(self):
    #     active_id = self._context.get('active_id')
    #     order = self.env['pms.materials'].browse(active_id)
    #     order.sudo().message_post(body=self.message)
    #     return True
    
    
    # To use the following function, make sure that the model has inherited mail.thread
    # _inherit = ['mail.thread', 'mail.activity.mixin']