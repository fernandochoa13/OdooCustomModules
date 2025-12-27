# -*- coding: utf-8 -*-
from odoo import fields, models, _


class ApproveBillsWizard(models.TransientModel):
    _name = 'approve.bills.wizard'
    _description = 'Approve Bills Wizard'

    user_ids = fields.Many2many("res.users", string="User", required=True)
    
    def generate_bill_approval_reports(self):
        self.ensure_one()
        context = {
            'default_user_ids': self.user_ids.ids, 
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'approve.bills.tree',
            'view_mode': 'tree',
            'res_model': 'approve.bills',
            'context': context,
        }


    
