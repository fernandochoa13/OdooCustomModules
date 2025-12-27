# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    @api.model
    def _get_payment_method_information(self):
        res = super()._get_payment_method_information()
        res['new_ach_fast_payment'] = {
            'mode': 'multi',
            'domain': [('type', '=', 'bank')],
            'currency_ids': self.env.ref("base.USD").ids,
            'country_id': self.env.ref("base.us").id
        }
        return res


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    payment_account_id = fields.Many2one(
        comodel_name='account.account',
        check_company=True,
        copy=False,
        ondelete='restrict',
        domain="[('deprecated', '=', False), "
                "('company_id', '=', company_id), "
                "('account_type', 'not in', ('asset_receivable', 'liability_payable')), "
                "'|', ('account_type', 'in', ('asset_current', 'liability_current', 'liability_credit_card')), ('id', '=', parent.default_account_id)]"
    )
