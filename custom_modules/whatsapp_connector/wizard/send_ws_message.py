from odoo import models, fields, api

class SendWSMessageWizard(models.TransientModel):
    _name = 'send.ws.message.wizard'
    _description = 'Send WS Message Wizard'

    body = fields.Text(string='Message Body', compute="_change_body", readonly=False)
    message_template = fields.Many2one('whatsapp.templates', string='Message Template')

    @api.depends('message_template')
    def _change_body(self):
        self.body = self.message_template.body

    def send_message(self):
        active_ids = self._context.get('partners_ids')
        for partner in active_ids:
            body_template = self.env['res.partner'].browse(partner).prepare_ws_template_message(self.body)
            self.env['res.partner'].browse(partner)._send_wa_message(body_template, partner, self.env['whatsapp.connector'].search([], limit=1).url)

        return {'type': 'ir.actions.act_window_close'}
    
    