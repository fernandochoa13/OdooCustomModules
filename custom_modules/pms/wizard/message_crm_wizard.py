from odoo import models, fields, api

from odoo import api, fields, models, _, Command
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference
import ast
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache
import requests
import json
#from intuitlib.exceptions import AuthClientError

from odoo import api, fields, models, Command, _
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.sql import create_index
from odoo.addons.web.controllers.utils import clean_action

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.tools.float_utils import float_round
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import frozendict

from collections import defaultdict
import math
import re
import string

class MessageCRMWizard(models.TransientModel):
    _name = 'message.crm.wizard'
    _description = 'Message CRM Wizard'

    def _default_silva_config(self):
        return self.env['sms.silvamedia'].search([], limit=1)

    sms = fields.Boolean(string='SMS Message', default=False)
    whatsapp = fields.Boolean(string='Whatsapp Message', default=False)
    message_text = fields.Text(string='Message Text')
    silva_config = fields.Many2one('sms.silvamedia', string='Silva Config', default=_default_silva_config)

    def create_user_contact(self, access_token, first_name, last_name, email, location_id, phone_number):
        try:
            new_user = requests.post("https://services.leadconnectorhq.com/contacts/",
                                    json={
                                            'firstName': first_name,
                                            'lastName': last_name,
                                            'name': f'{first_name} {last_name}',
                                            'email': email,
                                            'locationId': location_id,
                                            'phone': phone_number
                                        },
                                    headers={
                                            'Authorization': f'Bearer {access_token}',
                                            'Version': '2021-07-28',
                                            'Content-Type': 'application/json',
                                            'Accept': 'application/json'
                                        })
            print(new_user.json())
            new_user.raise_for_status()
            return new_user.json().get('contact').get('id')
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to create user contact: %s") % e)

    def send_sms_message(self, contact_id, toNumber, message, access_token):
        try:
            new_sms = requests.post("https://services.leadconnectorhq.com/conversations/messages",
                                    json={
                                            'contactId': contact_id,
                                            'message': message,
                                            'toNumber': toNumber,
                                            'type': 'SMS'
                                        },
                                    headers={
                                            'Authorization': f'Bearer {access_token}',
                                            'Version': '2021-07-28',
                                            'Content-Type': 'application/json',
                                            'Accept': 'application/json'
                                        })
            print(new_sms.json())
            new_sms.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to send SMS message: %s") % e)

    def send_ws_message(self, contact_id, toNumber, message, access_token):
        try:
            new_ws = requests.post("https://services.leadconnectorhq.com/conversations/messages",
                                json={
                                        'contactId': contact_id,
                                        'toNumber': toNumber,
                                        'message': message,
                                        'type': 'WhatsApp'
                                    },
                                headers={
                                        'Authorization': f'Bearer {access_token}',
                                        'Version': '2021-07-28',
                                        'Content-Type': 'application/json',
                                        'Accept': 'application/json'
                                    })
            print(new_ws.json())
            new_ws.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise UserError(_("Failed to send WhatsApp message: %s") % e)

    def send_message(self):
        contact_id = self._context.get('default_contact_id')
        partner_id = self._context.get('default_partner_id')
        invoice_id = self._context.get('default_invoice_id')
        first_name = self._context.get('default_first_name')
        last_name = self._context.get('default_last_name')
        email = self._context.get('default_email')
        phone_number = self._context.get('default_phone_number')
        partner_notes= self.env['res.partner'].browse(partner_id)
        invoice_notes = self.env['account.move'].browse(invoice_id)

        if not re.match(r'^\+1\d{10}$', phone_number):
            raise ValidationError(_("Phone number doesn't have a valid format."))
        
        if not contact_id:
            contact_id = self.create_user_contact(self.silva_config.access_token, first_name, last_name, email, self.silva_config.location_id, phone_number)
            self.env['res.partner'].browse(partner_id).write({'contact_id': contact_id})

        if invoice_id:
            if self.sms == True and self.whatsapp == False:
                self.send_sms_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                notes = f"SMS sent to {first_name} {last_name} with message: {self.message_text}"
                invoice_notes.message_post(body=notes)
            if self.whatsapp == True and self.sms == False:
                self.send_ws_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                notes = f"Whatsapp sent to {first_name} {last_name} with message: {self.message_text}"
                invoice_notes.message_post(body=notes)
            if self.sms == True and self.whatsapp == True:
                self.send_sms_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                self.send_ws_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                notes = f"SMS and Whatsapp sent to {first_name} {last_name} with message: {self.message_text}"
                invoice_notes.message_post(body=notes)

        if not invoice_id:
            if self.sms == True and self.whatsapp == False:
                self.send_sms_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                notes = f"SMS sent to {first_name} {last_name} with message: {self.message_text}"
                partner_notes.message_post(body=notes)
            if self.whatsapp == True and self.sms == False:
                self.send_ws_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                notes = f"Whatsapp sent to {first_name} {last_name} with message: {self.message_text}"
                partner_notes.message_post(body=notes)
            if self.sms == True and self.whatsapp == True:
                self.send_sms_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                self.send_ws_message(contact_id, phone_number, self.message_text, self.silva_config.access_token)
                notes = f"SMS and Whatsapp sent to {first_name} {last_name} with message: {self.message_text}"
                partner_notes.message_post(body=notes)


