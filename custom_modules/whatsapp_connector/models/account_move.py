from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def send_whatsapp_to_partner(self):
        partner = self.partner_id
        if partner:
            action = partner.action_send_whatsapp_message()
            return action
        else:
            # Handle the case when there is no partner assigned to the move
            pass