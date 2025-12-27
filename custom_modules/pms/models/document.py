from odoo import fields, models, _

class Documents(models.Model):
    _inherit = ["documents.document"]

    invoice_number = fields.Char(string="Invoice Number")
    amount = fields.Float(string="Amount")
    concept = fields.Char(string="Concept")
    date = fields.Date(string="Date")
    real_date = fields.Date(string="Real Date")
    payment_type = fields.Selection([("check", "Check"), ("online", "Online / CC"), ("material", "Material")], string="Payment Type", store=True, default="")
    customer = fields.Many2one("res.partner", string="Customer")
    company = fields.Many2one("res.company", string="Company*") # duplicate string
    invoice_link = fields.Char(string="Invoice Link")
