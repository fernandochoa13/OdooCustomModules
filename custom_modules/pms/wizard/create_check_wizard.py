from odoo import models, fields, api
import requests

from odoo.exceptions import ValidationError

class CreateCheckWizard(models.TransientModel):
    _name = 'create.check.wizard'
    _description = 'Create Check Wizard'

    amount = fields.Float(string='Amount', required=True)
    date = fields.Date(string='Date', required=True)
    memo = fields.Text(string='Memo')
    receiver = fields.Many2one('res.partner', string='Receiver', required=True)
    check_number = fields.Char(string='Check Number', readonly=False)
    
    @api.model
    def default_get(self, fields):
        res = super(CreateCheckWizard, self).default_get(fields)
        partner_id = self._context.get('default_partner_id')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if partner.exists():  # Ensure the partner exists
                res['check_number'] = str(int(partner.last_check_number) + 1)
        return res
    
    def create_check(self):
        bank_name = self._context.get('default_bank_name')
        bank_address = self._context.get('default_bank_address')
        bank_2address = self._context.get('default_bank_2address')
        bank_account_number = self._context.get('default_bank_account_number')
        bank_routing_number = self._context.get('default_bank_routing_number')
        partner_id = self._context.get('default_partner_id')


        partner = self.env['res.partner'].browse(partner_id)

        partner.last_check_number = self.check_number

        formatted_date = self.date.strftime('%Y-%m-%d')

        if not bank_name:
            raise ValidationError('The bank name cannot be empty.')
        if not bank_address:
            raise ValidationError('The bank address cannot be empty.')
        if not bank_2address:
            raise ValidationError('The second bank address cannot be empty.')
        if not bank_account_number:
            raise ValidationError('The bank account number cannot be empty.')
        if not bank_routing_number:
            raise ValidationError('The bank routing number cannot be empty.')
        if not partner_id:
            raise ValidationError('The partner ID cannot be empty.')
        if not partner.name:
            raise ValidationError('The partner ID cannot be empty.')
        if not partner.email:
            raise ValidationError('The partner email cannot be empty.')
        if not partner.phone and not partner.mobile:
            raise ValidationError('The partner phone or mobile cannot be empty.')
        if not partner.street:
            raise ValidationError('The partner street cannot be empty.')
        if not partner.city:
            raise ValidationError('The partner city cannot be empty.')
        if not partner.state_id.name:
            raise ValidationError('The partner state cannot be empty.')
        if not partner.zip:
            raise ValidationError('The partner zip cannot be empty.')
        if not partner.authorized_signature:
            raise ValidationError('The partner authorized signature cannot be empty.')
        if not self.amount:
            raise ValidationError('Amount can not be zero.')
        
        past_check = self.env['check.maker.payment'].search(['&', ('check_number', '=', self.check_number), ('contact', '=', partner_id)])
        if past_check:
            raise ValidationError('A check with this number already exists for this partner.')

        check_data = {
            'receiver': self.receiver.name,
            'amount': self.amount,
            'date': formatted_date,
            'memo': self.memo,
            'status': 'draft',
            'check_number': self.check_number,
            'bank_name': bank_name,
            'bank_address': bank_address,
            'bank_2address': bank_2address,
            'bank_account': bank_account_number,
            'bank_routing': bank_routing_number,
            'company_name': partner.name,
            'company_email': partner.email,
            'company_phone': partner.phone or partner.mobile,
            'company_address': partner.street,
            'company_2address': f'{partner.city}, {partner.state_id.name}, {partner.zip}',
            'authorized_signature': partner.authorized_signature,
            'contact': partner_id,

        }

        check_maker = self.env['check.maker.payment'].create(check_data)

        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'check.maker.payment',
            'view_mode': 'form',
            'res_id': check_maker.id,
            'target': 'current',  
        }

        return action

    

