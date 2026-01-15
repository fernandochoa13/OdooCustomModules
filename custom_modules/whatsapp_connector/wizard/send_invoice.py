from odoo import models, fields
from odoo.tools.misc import get_lang

class SendInvoice(models.TransientModel):
    _inherit = 'account.move.send'

    send_whatsapp = fields.Boolean(string='Send WhatsApp Message', default=True)
    whatsapp_body = fields.Text(string='WhatsApp Body')

    def _send_whatsapp_message(self, invoice):
        if self.send_whatsapp:
            url = self.env['whatsapp.connector'].search([], limit=1).url
            invoice.partner_id._send_wa_message(self.whatsapp_body, invoice.partner_id.id, url)

    
    def send_and_print_action(self):
        self.ensure_one()
        # Send the mails in the correct language by splitting the ids per lang.
        # This should ideally be fixed in mail_compose_message, so when a fix is made there this whole commit should be reverted.
        # basically self.body (which could be manually edited) extracts self.template_id,
        # which is then not translated for each customer.
        if self.composition_mode == 'mass_mail' and self.template_id:
            active_ids = self.env.context.get('active_ids', self.res_id)
            active_records = self.env[self.model].browse(active_ids)
            langs = set(active_records.mapped('partner_id.lang'))
            for lang in langs:
                active_ids_lang = active_records.filtered(lambda r: r.partner_id.lang == lang).ids
                self_lang = self.with_context(active_ids=active_ids_lang, lang=get_lang(self.env, lang).code)
                self_lang.onchange_template_id()
                self_lang._send_email()
        else:
            active_record = self.env[self.model].browse(self.res_id)
            lang = get_lang(self.env, active_record.partner_id.lang).code
            self.with_context(lang=lang)._send_email()
        
        if self.send_whatsapp:
                active_ids = self.env.context.get('active_ids', self.res_id)
                active_records = self.env[self.model].browse(active_ids)
                for invoice in active_records:
                    self._send_whatsapp_message(invoice)
        
        
        if self.is_print:
            return self._print_document()
        
        return {'type': 'ir.actions.act_window_close'}