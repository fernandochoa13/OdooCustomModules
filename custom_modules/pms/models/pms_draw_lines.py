from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

class pms_draw_lines(models.Model):
    _name = "pms.draw.lines"
    _description = "Table for Draw lines"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    steps = fields.Selection(selection=[
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
    draw_id = fields.Many2one("pms.draws", string="Draw ID")
    property_draw = fields.Many2one(related="draw_id.address", string='Property Address', readonly=True)
    amount_drawed = fields.Monetary(string="Amount", required=True, currency_field='company_currency_id', store=True)
 
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Accounting Company',
        default=lambda self: self.env.company
    )

    company_currency_id = fields.Many2one(
        string='Company Currency',
        related='company_id.currency_id', readonly=True
    )

