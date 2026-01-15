from odoo import api, fields, models, _
from datetime import timedelta

class FollowupLine(models.Model):
    _inherit = 'account_followup.followup.line'

    send_whatsapp = fields.Boolean(string='Send WhatsApp')
    whatsapp_template_id = fields.Many2one('whatsapp.templates', string='WhatsApp Template')