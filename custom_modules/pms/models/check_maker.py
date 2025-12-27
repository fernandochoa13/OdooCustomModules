from odoo import models, fields
import requests
import json
from odoo import api, models, fields, http
import requests
import base64
import inflect
from datetime import datetime
from odoo.exceptions import ValidationError, UserError

from urllib.parse import urlencode

class CheckMakerPayment(models.Model):
    _name = 'check.maker.payment'
    _description = 'Check Payment'

    name = fields.Char(string='Name', compute="_create_name", readonly=True)
    check_number = fields.Char(string='Check Number', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)
    amount_text = fields.Char(string='Amount in Words', readonly=True)
    company_name = fields.Char(string='Company', readonly=True)
    company_address = fields.Char(string='Address', readonly=True)
    company_2address = fields.Char(string='Second Address', readonly=True)
    company_email = fields.Char(string='Email', readonly=True)
    company_phone = fields.Char(string='Phone', readonly=True)
    receiver = fields.Char(string='Payee', readonly=True)
    bank_name = fields.Char(string='Bank', readonly=True)
    bank_address = fields.Char(string='Bank Address', readonly=True)
    bank_2address = fields.Char(string='Second Bank Address', readonly=True)
    bank_account = fields.Char(string='Account', readonly=True)
    bank_routing = fields.Char(string='Routing', readonly=True)
    memo = fields.Char(string='Memo', readonly=True)
    authorized_signature = fields.Binary(string='Authorized Signature', readonly=True)
    contact = fields.Many2one('res.partner', string='Contact', readonly=True)
    print_date = fields.Date(string='Print Date', readonly=False)
    printed = fields.Boolean(string='Printed', readonly=True)

    status = fields.Selection([
        ('draft', 'To Print'),
        ('posted', 'Printed'),
        ('void', 'Void'),
    ], string='Status', default='draft')

    @api.depends('receiver', 'check_number', 'date')
    def _create_name(self):
        for record in self:
            record.name = f'Check {record.receiver} - #{record.check_number} - {record.date}'

    def create_check(self):
        if self.printed == True and self.status != 'void':
            raise ValidationError("This check has already been printed.")
        else:
            base_url = self.env['check.url'].search([], limit=1).url
            amount_number = self.amount
            if amount_number.is_integer():
                amount_number = int(amount_number)
                amount_text = inflect.engine().number_to_words(amount_number).title()
                amount_text = amount_text.replace(" And ", " ")
                formatted_amount = f"{amount_number:,}" + ".00"
                cents = "00"
            else:
                integer_part = str(amount_number).split(".")[0]
                decimal_part = str(amount_number).split(".")[1]

                if len(decimal_part) == 1:
                    decimal_part = decimal_part + "0"

                amount_text = inflect.engine().number_to_words(integer_part).title()
                amount_text = amount_text.replace(" And ", " ")
                formatted_amount = f"{amount_number:,.2f}"
                cents = decimal_part 

            formatted_date = self.date.strftime('%m/%d/%Y')

            signature_base64 = base64.b64encode(self.authorized_signature).decode('utf-8') if self.authorized_signature else None

            payload = json.dumps({
                "company_name": self.company_name,
                "company_address": self.company_address,
                "company_2address": self.company_2address,
                "company_email": self.company_email,
                "company_phone": self.company_phone,
                "bank_name": self.bank_name,
                "bank_address": self.bank_address,
                "bank_2address": self.bank_2address,
                "bank_account": self.bank_account,
                "bank_routing": self.bank_routing,
                "check_number": self.check_number,
                "date": str(formatted_date),
                "receiver": self.receiver,
                "amount": str(formatted_amount),
                "memo": self.memo[:90],
                "cents": str(cents),
                "amount_text": amount_text,
                "signature": signature_base64,
            })

            headers={'Content-Type': 'application/json'}

            if self.status == 'void':
                response = requests.post(f"{base_url}/render_check_voided", data=payload, headers=headers)
                if response.status_code == 200:
                    print("Check rendered successfully")
                    return {
                        'type': 'ir.actions.act_url',
                        'url': f"{base_url}/render_check_voided",
                        'target': 'new',
                    }
                else:
                    print("Failed to render check")
                    return None
            else:
                response = requests.post(f"{base_url}/render_check", data=payload, headers=headers)
                if response.status_code == 200:
                    print("Check rendered successfully")
                    return {
                        'type': 'ir.actions.act_url',
                        'url': f"{base_url}/render_check",
                        'target': 'new',
                    }
                else:
                    print("Failed to render check")
                    return None

    def create_checks(self):
        statuses = self.mapped('status')
    
        if len(set(statuses)) > 1:
            raise ValidationError("You cannot print checks with different statuses. Please select records with the same status.")
    
        for record in self:
            if record.printed and record.status != 'void':
                raise ValidationError(f"Some checks have already been printed and are not void. You cannot reprint these checks.")

        checks_data = []
        for record in self:
            amount_number = record.amount
            if amount_number.is_integer():
                amount_number = int(amount_number)
                amount_text = inflect.engine().number_to_words(amount_number).title()
                amount_text = amount_text.replace(" And ", " ")
                formatted_amount = f"{amount_number:,}" + ".00"
                cents = "00"
            else:
                integer_part = str(amount_number).split(".")[0]
                decimal_part = str(amount_number).split(".")[1]

                if len(decimal_part) == 1:
                    decimal_part = decimal_part + "0"

                amount_text = inflect.engine().number_to_words(integer_part).title()
                amount_text = amount_text.replace(" And ", " ")
                formatted_amount = f"{amount_number:,.2f}"
                cents = decimal_part 

            formatted_date = record.date.strftime('%m/%d/%Y')

            signature_base64 = base64.b64encode(record.authorized_signature).decode('utf-8') if record.authorized_signature else None

            checks_data.append({
                "company_name": record.company_name,
                "company_address": record.company_address,
                "company_2address": record.company_2address,
                "company_email": record.company_email,
                "company_phone": record.company_phone,
                "bank_name": record.bank_name,
                "bank_address": record.bank_address,
                "bank_2address": record.bank_2address,
                "bank_account": record.bank_account,
                "bank_routing": record.bank_routing,
                "check_number": record.check_number,
                "date": str(formatted_date),
                "receiver": record.receiver,
                "amount": str(formatted_amount),
                "memo": record.memo,
                "cents": str(cents),
                "amount_text": amount_text,
                "signature": signature_base64,
            })

        payload = json.dumps({"checks": checks_data})
        base_url = self.env['check.url'].search([], limit=1).url
        headers = {'Content-Type': 'application/json'}

        if record.status == 'void':
            response = requests.post(f"{base_url}/render_checks_voided", data=payload, headers=headers)
            if response.status_code == 200:
                print("Checks rendered successfully")
                for record in self:
                    record.status = 'posted'
                    record.printed = True
                    if not record.print_date:
                        record.print_date = datetime.now()
                return {
                    'type': 'ir.actions.act_url',
                    'url': f"{base_url}/render_checks_voided",
                    'target': 'new',
                }
            else:
                print("Failed to render checks")
                return None
        else:
            response = requests.post(f"{base_url}/render_checks", data=payload, headers=headers)

            if response.status_code == 200:
                print("Checks rendered successfully")
                for record in self:
                    record.status = 'posted'
                    record.printed = True
                    if not record.print_date:
                        record.print_date = datetime.now()
                return {
                    'type': 'ir.actions.act_url',
                    'url': f"{base_url}/render_checks",
                    'target': 'new',
                }
            else:
                print("Failed to render checks")
                return None


    def confirm_check(self):
        self.status = 'posted'
        return True

    def void(self):
        self.status = 'void'
        return True
    
    def draft(self):
        self.status = 'draft'
        return True
    
    def update_contact_id(self):
        for record in self:
            record.contact = record.env['res.partner'].search([('name', '=', record.company_name)]).id