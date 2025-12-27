from odoo import fields, models, _
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)

class PartnerVerifyWizard(models.Model):
        _name = "partner.verify.wizard"
        _description = "Partner Verify Wizard"

        employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
        employee_pin = fields.Char(string='Employee PIN', required=True)

        def open_partner_wizard(self):
            selected_records = self.env.context.get('active_ids')

            pin_verification = self.env['hr.employee'].search([('id', '=', self.employee_id.id), ('pin', '=', self.employee_pin)])

            if pin_verification and pin_verification.access_to_modify_records == True:
                return {
                    'name': 'Partner Selector Wizard',
                    'type': 'ir.actions.act_window',
                    'res_model': 'partner.selector.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'active_ids': selected_records,
                                'company_id': self.env.company.id},
                }
            else:
                raise ValidationError(_('Invalid Employee PIN or Employee does not have access to modify records.'))

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def open_partner_verify_wizard(self):
        return {
            'name': 'Verify Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'partner.verify.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_ids': self.ids,
            },
        }
 


class PartnerSelector(models.Model):
        _name = "partner.selector.wizard"
        _description = "Partner Selector Wizard"

        company_id = fields.Many2one('res.company', string='Company', default=lambda self: self._context.get('company_id'))

        partner_to_change = fields.Many2one(
        'res.partner', 
        string='Partner to change', 
        required=False,
        # domain="[('company_id', '=', company_id)]"
        )

        blank_partner = fields.Boolean(string="Set partner as null (only applicable for journal entries)", default=True)

        # def change_partner(self):
        #     selected_records = self._context.get('active_ids')
        #     partner_to_change = self.partner_to_change

        #     for record in self.env['account.move.line'].browse(selected_records):
        #         record.partner_id = partner_to_change

        #     return {'type': 'ir.actions.act_window_close'}
        
        def change_partner(self):
            selected_records = self._context.get('active_ids')

            # If the user wants to set the partner to blank and has NOT selected a new partner.
            if self.blank_partner and not self.partner_to_change:
                new_partner_id = False
            # If the user has selected a new partner.
            elif self.partner_to_change:
                new_partner_id = self.partner_to_change.id
            else:
                # If no action is specified (no new partner and no blank partner check), do nothing.
                return {'type': 'ir.actions.act_window_close'}

            # Use a custom context key to bypass validation checks.
            self.env['account.move.line'].browse(selected_records).with_context(allow_partner_id_change=True).write({'partner_id': new_partner_id})

            return {'type': 'ir.actions.act_window_close'}