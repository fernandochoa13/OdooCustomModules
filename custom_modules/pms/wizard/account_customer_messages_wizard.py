from odoo import models, fields, api

class account_customer_messages_wizard(models.TransientModel):
    _name = 'account.customer.message.wizard'
    _description = 'Customer Messages Wizard'

    customer = fields.Many2one('res.partner', string='Select Customer')
    messages = fields.Many2one('mail.message', string='Messages')


    def get_customer_message_view(self):
        self.ensure_one()
        ctx = {"customer": self.customer.id,
               "messages": self.messages.id}
        return {
            'type': 'ir.actions.act_window',
            'name': ('view_account_message_tree'),
            'res_model': 'account.customer.message',
            'view_mode': 'tree',
            'context': ctx}