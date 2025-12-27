from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.fields import Command

class pms_close_property(models.TransientModel):
    _name = 'pms.close.property'
    _description = 'Close Property to residential Unit'

    property = fields.Many2one("pms.property", string='Property', domain="[('residential_unit_closure', '=', False)]", required=True)    
    company = fields.Many2one("res.company", string="Company", required=True)
    date = fields.Date(string="Date", required=True)
    total_gl_amount = fields.Float(string="Total GL Amount", readonly=True)
    item_details = fields.Boolean(string="Check Construction Report so no items are left behind and it checks with gl amount", default=False, required=True)
    note = fields.Text(string="Note")

    final_amount = fields.Float(string="Final Amount")


    @api.onchange('property')
    def _onchange_property(self):
        if self.property:
            company = self.env['res.company'].search([("partner_id", "=", self.property.partner_id.id)])
            if len(company.ids) > 0:
                self.company = company


    @api.depends("property", "company")
    def _get_total_gl_amount(self):
        for record in self:
            # Direct Acquisition account
            if record.property and record.company:
                direct_acquisition_account = record.env["account.account"].search(["&", ("code", "=", "1000201"), ("company_id", "=", record.company.id)])
                total_gl_amount = record.env["account.analytic.line"].search(["&", ("general_account_id", "=", direct_acquisition_account.id), ("account_id", "=", record.property.analytical_account.id)]).mapped("amount").sum()
                if total_gl_amount == 0:
                    total_gl_amount = 0
                else:
                    record.total_gl_amount = total_gl_amount


    def cancel(self):
        return {'type': 'ir.actions.act_window_close'}
    
    def create_closing(self):
        for record in self:
            if self.company == False:
                raise ValidationError("Please select a company")

            if self.date == False:
                raise ValidationError("Please select a date")
            
            if self.item_details == False:
                raise ValidationError("Please check the item details")

            direct_acquisition_account = self.env["account.account"].search(["&", ("code", "=", "1000201"), ("company_id", "=", record.company.id)])
            residential_unit = self.env["account.account"].search(["&", ("code", "=", "1000202"), ("company_id", "=", record.company.id)])

            # Create Journal Entry
            
            lines = []
            line_debit = {
                'account_id': direct_acquisition_account.id,
                'debit': 0.0,
                'credit': self.final_amount,
            }
            line_credit = {
                'account_id': residential_unit.id,
                'debit': self.final_amount,
                'credit': 0.0,
            }

            lines.append(Command.create(line_debit))
            lines.append(Command.create(line_credit))

            

            journal = {
                "date": record.date,
                'move_type': 'entry',
                "ref": f"Closing Property of {record.property.name}",
                "company_id": record.company.id,
                "line_ids": []   
            }

            journal['line_ids'] += lines

            move = self.env['account.move'].sudo().create(journal)
            move.action_post()

            record.property.residential_unit_closure = True
            record.property.residential_unit_date = record.date

            action = {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
            'target': 'current',  
            }

            return action


