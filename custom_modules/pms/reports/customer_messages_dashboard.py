from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch

from odoo import api, fields, models, _, Command, tools
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference



class CustomerMessagesDashboard(models.Model):
    _name = "customer.messages.dashboard"
    _description = "General Customer Messages Dashboard"
    _auto = False

    id = fields.Integer(readonly=True)
    date = fields.Date(string='Date', readonly=True)
    author = fields.Char(string='Author', readonly=True)
    subject_id = fields.Char(string='Subject', readonly=True)
    doc_model = fields.Char(string='Document Model', readonly=True)
    doc_id = fields.Integer(string='Document ID', readonly=True)
    body_message = fields.Html(string='Body', readonly=True)
    account_move_id = fields.Integer(string='Account Move ID', readonly=True)
    res_partner_id = fields.Integer(string='Res Partner ID', readonly=True)
    move_name = fields.Char(string='Move Name', readonly=True)
    partner_name = fields.Char(string='Partner Name', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'customer_messages_dashboard')
        self._cr.execute("""
            CREATE OR REPLACE VIEW customer_messages_dashboard AS (
                SELECT 
                mm.id AS id,
                mm.date AS date,
                rp.name AS author,
                mm.subject AS subject_id,
                mm.model AS doc_model,
                mm.res_id AS doc_id,
                mm.body AS body_message,
                am.id AS account_move_id,
                am.name AS move_name,
                rp2.id AS res_partner_id,
                rp3.name AS partner_name
            FROM mail_message mm
            LEFT JOIN res_partner rp ON mm.author_id = rp.id
            LEFT JOIN account_move am ON mm.model = 'account.move' AND mm.res_id = am.id
            LEFT JOIN res_partner rp2 ON mm.model = 'res.partner' AND mm.res_id = rp2.id
            LEFT JOIN res_partner rp3 ON am.partner_id = rp3.id
            WHERE mm.model IN ('account.move', 'res.partner')
            AND mm.is_internal IS NOT TRUE
            AND mm.message_type != 'notification'
            )
        """)

    
    def view_document(self):
        if self.doc_model == 'account.move':
            return {
                'type': 'ir.actions.act_window',
                'name': ('view_move_form'),
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.account_move_id,}
        
        elif self.doc_model == 'res.partner':
            return {
                'type': 'ir.actions.act_window',
                'name': ('view_partner_form'),
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.res_partner_id}
