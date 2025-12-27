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


class AccountCustomerMessages(models.Model):
    _name = "account.customer.message"
    _description = "Table for Customer Messages"
    _auto = False

    id = fields.Integer(readonly=True)
    date = fields.Datetime(string='Date', readonly=True)
    subject_id = fields.Char(string='Subject', readonly=True)
    author = fields.Char(string='Author', readonly=True)
    doc_model = fields.Char(string='Document Model', readonly=True)
    doc_id = fields.Integer(string='Document ID', readonly=True)
    body_message = fields.Html(string='Body', readonly=True)
    partner_id = fields.Integer(string='Partner ID', readonly=True)
    partner_name = fields.Char(string='Partner Name', readonly=True)
    move_id = fields.Many2one("account.move", string='Move ID')


    @property
    def _table_query(self):
        customer_id = self.env.context.get('customer')
        return """
                SELECT sub2.*, res_partner.name AS partner_name

                FROM

                (SELECT sub.*, 
                CASE WHEN doc_model = 'account.move' THEN account_move.partner_id
                WHEN doc_model = 'res.partner' THEN doc_id
                END AS partner_id

                FROM

                (SELECT mail_message.id as id, mail_message.date as date, mail_message.subject as subject_id, res_partner.name as author, mail_message.model as doc_model, mail_message.res_id as doc_id, mail_message.body as body_message, mail_message.message_type as message_type,
                CASE WHEN mail_message.model = 'account.move' THEN mail_message.res_id
                END as move_id

                FROM mail_message
                
                LEFT JOIN res_partner ON mail_message.author_id = res_partner.id) sub

                LEFT JOIN account_move ON move_id = account_move.id) sub2

                LEFT JOIN res_partner ON partner_id = res_partner.id

                WHERE partner_id = %s AND message_type IN ('comment', 'email', 'sms')

                """ % (customer_id)
    
    def view_document(self):
        
        if self.doc_model == 'account.move':
            return {
                'type': 'ir.actions.act_window',
                'name': ('view_move_form'),
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.move_id.id,}
                
        
        elif self.doc_model == 'res.partner':
            return {
                'type': 'ir.actions.act_window',
                'name': ('view_partner_form'),
                'res_model': 'res.partner',
                'view_mode': 'form',
                'res_id': self.doc_id}
