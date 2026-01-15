from odoo import models, fields, api


class SendInvoiceWhatsApp(models.TransientModel):
    _name = 'account.move.send.whatsapp'
    _description = 'Send Invoice via WhatsApp'

    move_ids = fields.Many2many('account.move', string='Invoices')
    send_whatsapp = fields.Boolean(string='Send WhatsApp Message', default=True)
    whatsapp_body = fields.Text(string='WhatsApp Body')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'account.move':
            res['move_ids'] = [(6, 0, self.env.context.get('active_ids', []))]
        return res

    def _send_whatsapp_message(self, invoice):
        if self.send_whatsapp and self.whatsapp_body:
            url = self.env['whatsapp.connector'].search([], limit=1).url
            if url and invoice.partner_id:
                invoice.partner_id._send_wa_message(self.whatsapp_body, invoice.partner_id.id, url)

    def action_send_whatsapp(self):
        self.ensure_one()
        for invoice in self.move_ids:
            self._send_whatsapp_message(invoice)
        return {'type': 'ir.actions.act_window_close'}
