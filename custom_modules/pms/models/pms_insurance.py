from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime

class pms_insurance(models.Model):
    _name = "pms.insurance"
    _description = "Insurance Policies for properties"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(required=True, string="Policy Number")
    insurance_start = fields.Date(string="Insurance Policy Start Date")
    insurance_end = fields.Date(string="Insurance Policy End Date")
    total_coverage_amount = fields.Monetary(string="Coverage Amount", currency_field='company_currency_id', compute="_total_coverage_amount_calc", store=True, readonly=False)
    total_premiun_amount = fields.Monetary(string="Premiun Amount", currency_field='company_currency_id', compute="_total_premiun_amount_calc", store=True, readonly=True)
    days_to_expire = fields.Float(string="Days to expire", compute="_days_to_expire", store=True)
    active = fields.Boolean(string="Active", default=True)
    open_claim = fields.Boolean(string="Open Claim")
    claim_description = fields.Char(string="Description of Claim")
    insurance_provider = fields.Many2one("res.partner", string="Insurance Provider")
    insurance_agent = fields.Many2one("res.partner", string="Insurance Agent", tracking=True)
    insurance_type = fields.Selection(selection=[
        ("normal_insurance", "Builder Risk"),
        ("flood_insurance", "Flood Insurance"),
        ("liability_insurance", "Liability Insurance"),
        ("rental_property_insurance", "Rental Property Insurance")], string="Insurance Type", default="normal_insurance")
    insurance_line = fields.One2many("pms.insuranceline", "insurance_header")

    # === Currency fields === #
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Accounting Company',
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True
    )

    # === Computed Fields === #
    @api.depends("insurance_end")
    def _days_to_expire(self):
        for record in self:
            print(record.insurance_end)
            if record.insurance_end:
                timedelta = record.insurance_end - datetime.today().date()
                record.days_to_expire = timedelta.days + float(timedelta.seconds) / 86400
            else:
                record.days_to_expire = 0
    
    def oopen_claim(self):
        for record in self:
            record.open_claim = True

    def close_claim(self):
        for record in self:
            record.open_claim = False

    @api.depends("insurance_line")
    def _total_coverage_amount_calc(self):
        for record in self:
            if record.insurance_type == "liability_insurance":
                pass
            else:
                total = 0.00
                for line in record.insurance_line:
                    total += line.coverage_amount
                record.total_coverage_amount = total

        
    @api.depends("insurance_line")
    def _total_premiun_amount_calc(self):
        for record in self:
            total = 0.00
            for line in record.insurance_line:
                total += line.premiun_amount
            record.total_premiun_amount = total

    
    

    # === Documents functions to override === #
    def _get_document_folder(self):
        return self.env["documents.folder"].search([("name", "=", "Properties")])
