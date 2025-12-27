from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date


class contact_liabilityinsurance(models.Model):
    _name = "contact.liabilityinsurance"
    _description = "Liability Insurance"


    liability_insurance_name = fields.Char(string="Liability Insurance Name")
    liability_insurance_attachment = fields.Binary(string='Liability Insurance Attachment', attachment=True)
    liability_insurance_expiration_date = fields.Date(string='Liability Insurance Expiration Date')
    days_to_expire = fields.Integer(string='Days to Expire', compute='_compute_days_to_expire', store=True)
    insurance_for = fields.Many2one("res.partner", string="Certificate Holder")
    original_partner = fields.Many2one("res.partner", string="Insured")
    insurance_type = fields.Selection(selection=[
        ("wc", "Woker Compensation"),
        ("coi", "Commercial Liability")], string="Insurance Type", default="wc")
    active = fields.Boolean(string="Active", default=True)


    def _compute_days_to_expire(self):
        for record in self:
            if record.liability_insurance_expiration_date:
                current_date = date.today()
                days = (record.liability_insurance_expiration_date - current_date).days
                record.days_to_expire = days
            else:
                record.days_to_expire = 0