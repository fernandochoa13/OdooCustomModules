from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime

class pms_liability_insurance_rent(models.Model):
    _name = "pms.liability.insurance.rent"
    _description = "Liability Insurance rent"

    name = fields.Char(required=True, string="Policy Number")
    insurance_start = fields.Date(string="Insurance Policy Start Date")
    insurance_end = fields.Date(string="Insurance Policy End Date")
    days_to_expire = fields.Float(string="Days to expire", compute="_days_to_expire", store=True)