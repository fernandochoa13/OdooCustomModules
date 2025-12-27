from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

class pms_draw_items(models.Model):
    _name = "pms.draw.items"
    _description = "Table for Draw items"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']
 
    draw_step = fields.Selection(selection=[
        ("permits_plan", "Soft Costs (Plans/Permits/Fees)"),
        ("demolition_dumpsters", "Demolition & Trash Haul"),
        ("slab", "Slab"),
        ("foundation", "Foundation"),
        ("framing", "Framing"),
        ("plumbing_finish", "Plumbing Finish Materials"),
        ("plumbing_rough", "Plumbing Install / Rough"),
        ("electrical_finish", "Electrical Finish Materials"),
        ("elect_rough", "Electrical Install / Rough"),
        ("metal_works", "Metal Works (iron, etc.)"),
        ("vanity_mirrors", "3 Vanity Mirrors"),
        ("hvac", "Hvac"),
        ("roof", "Roof"),
        ("pressure_wash", "Pressure Wash"),
        ("insulation", "Insulation"),
        ("drywall_tapeing", "Drywall / Tapeing"),
        ("tile_finish", "Tile Finish Materials"),
        ("tile_install", "Tile Installations"),
        ("doors_windows", "Doors/Windows"),
        ("finish_carpentry", "Finish Carpentry"),
        ("paint_specialties", "Paint / Specialties"),
        ("windows", "Windows"),
        ("flooring", "Flooring"),
        ("stairs", "Stairs"),
        ("outdoor_patio", "Outdoor Patio"),
        ("hardware", "Hardware"),
        ("pool", "Pool"),
        ("appliances", "Appliances"),
        ("countertops", "Countertops (w/Install)"),
        ("kitchen_cabinets", "Kitchen Cabinets"),
        ("general_labor", "General Labor"),
        ("landscaping", "Landscaping"),
        ("hardscape_driveway", "Hardscape / Driveway"),
        ("bathrooms", "Bathrooms"),
        ("fence", "Fence"),
        ("pm_fee", "PM Fee"),
        ("open_item", "Open Item"),
        ("open_item2", "Open Item"),
        ("open_item3", "Open Item"),
        ("staging_cleanup", "Staging & Final Cleanup"),
        ("contingency", "Contingency"),
        ("owner_contribution", "Owner's Contribution"),

        ], string="Steps",
        readonly=False, copy=False, index=True, tracking=True,
        default='')
    total_amount = fields.Monetary(string="Total Amount Drawed", compute="_calculate_total_amount", currency_field='company_currency_id', store=True)
    budget = fields.Monetary(string="Budget", required=True, currency_field='company_currency_id')
    balance = fields.Monetary(string="Balance", compute="_calculate_balance", currency_field='company_currency_id')
    loan_id = fields.Many2one("pms.loans", string="Loan ID", readonly=True)
    requested = fields.Boolean(string="Requested", default=False)

    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Accounting Company',
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True
    )

    @api.depends("total_amount", "budget")
    def _calculate_balance(self):
        for record in self:
            record.balance = record.budget - record.total_amount

    # Make the function _calculate_total_amount update if there are changes in the pme_draw_lines table
        
    @api.depends("draw_step", "loan_id", "loan_id.draw_history", "loan_id.draw_history.draw_lines")
    def _calculate_total_amount(self):
        for record in self:
            test = record.env["pms.draw.lines"].sudo().search(["&", ("steps", "=", record.draw_step), ("draw_id.loan_id.id", "=", record.loan_id.id)])
            record.total_amount = sum(test.sudo().mapped("amount_drawed"))


            
            

    
