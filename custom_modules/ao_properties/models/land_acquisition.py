
from odoo import models, fields, api


class LandAcquisition(models.Model):

    _name = 'land.acquisition'
    _description = 'Land Acquisition'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    parcel_id = fields.Char(string="Parcel Id", required=True)
    address = fields.Char(string="Address")
    name = fields.Char(string='Name', compute="_compute_name", store=True, tracking=True)
    county = fields.Selection(string='County', selection=[
        ('marion', 'Marion'),
        ('lee', 'Lee'),
        ('highlands', 'Highlands'),
        ('polk', 'Polk'),
        ('osceola', 'Osceola'),
        ('lake', 'Lake'),
        ('charlotte', 'Charlotte'),
        ('volusia', 'Volusia')
    ])
    inspection_date = fields.Date(string="Inspection Date")
    date_start = fields.Datetime(string='Start Date')
    date_end = fields.Datetime(string='End Date')
    user_id = fields.Many2one(string='Agent', comodel_name='res.users')
    company_id = fields.Many2one(string='Company', comodel_name='res.company')
    emd = fields.Monetary(string="EMD", help="Escrow Money Deposit", currency_field='currency_id')
    currency_id = fields.Many2one(string='Currency', readonly=True, related='company_id.currency_id')
    tag_ids = fields.Many2many(string='Tags', relation='land_acquisition_tag_ids', comodel_name='land.acquisition.tag')
    notes = fields.Html(string='Notes')
    zoning = fields.Selection(string='Zoning', selection=[
        ('single_family', 'Single Family'),
        ('duplex', 'Duplex'),
        ('commercial', 'Commercial')
    ])
    closing_date = fields.Date(string="Closing Date")
    purchase_price = fields.Monetary(string='Purchase Price', currency_field="currency_id")
    sold_price = fields.Monetary(string='Sold Price', currency_field="currency_id")
    buyer_id = fields.Many2one(string="Buyer", comodel_name='res.partner')
    profit_margin = fields.Monetary(
        string="Profit Margin",
        currency_field='currency_id',
        compute='_compute_profit_margin'
    )
    stage_id = fields.Many2one(string='Stage', comodel_name='land.acquisition.stage')
    color = fields.Integer(string="Color")
    priority = fields.Boolean(string="Priority")
    sequence = fields.Integer(string="Sequence", default=1)
    kanban_state = fields.Selection(selection=[
        ('normal', 'In Progress'),
        ('done', 'Ready'),
        ('blocked', 'Blocked')
    ], string="Kanban State", default="normal")
    property_model_id = fields.Many2one(string="Model", comodel_name='plus.property.model')
    scrow_status = fields.Selection(string="Scrow Status", selection=[
        ('sent', 'Sent'),
        ('not_sent', 'Not Sent'),
    ])
    lot_inspection = fields.Selection(string="Lot Inspection", selection=[
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('hold', 'Hold'),
        ('sent_for_inspection', 'Sent for Inspection'),
    ])
    sent_for_survey = fields.Selection(string="Sent For Survey", selection=[
        ('yes', 'Yes'),
        ('no', 'No'),
        ('hold', 'Hold'),
        ('cancellation_sent', 'Cancellation Sent'),
    ])
    file_open = fields.Selection(string="File Open", selection=[
        ('sent', 'Sent'),
        ('not_sent', 'Not Sent'),
        ('pending', 'Pending'),
        ('opened', 'Opened'),
    ])
    loan = fields.Selection(string="Loan", selection=[
        ('yes', 'Yes'),
        ('no', 'No'),
    ])
    week_number = fields.Integer(string="Week Number")
    business_decision = fields.Selection(string="Business Decision", selection=[
        ('build', 'Build'),
        ('wholesale', 'Wholesale'),
        ('hold', 'Hold'),
        ('canceled', 'Canceled'),
        ('pending', 'Pending'),
    ])
    acquisition_status = fields.Selection(string="Acquisition Status", selection=[
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('probate', 'Probate'),
    ])
    turtle_tree_inspection = fields.Text(string="Turtle/Tree Inspection")
    scrub_jays = fields.Selection(string="Scrub Jays", selection=[
        ('yes', 'Yes'),
        ('no', 'No'),
    ])
    hoa = fields.Selection(string="HOA", selection=[
        ('yes', 'Yes, HOA'),
        ('no', 'No, HOA'),
    ])
    utility_report = fields.Selection(string="Utility Report", selection=[
        ('well_septic', 'Well/Septic'),
        ('city_water_sewer', 'City Water/Sewer'),
        ('city_water_sewer_waiver', 'City Water/Sewer Waiver'),
        ('well_sewer_waiver', 'Well/Sewer Waiver'),
        ('city_water_septic', 'City Water/Septic'),
    ])
    floodzone = fields.Boolean(string="Floodzone")

    @api.depends('parcel_id', 'address')
    def _compute_name(self):
        for land_acquisition in self:
            if not land_acquisition.parcel_id:
                land_acquisition.name = ''
                continue
            if land_acquisition.parcel_id and not land_acquisition.address:
                land_acquisition.name = land_acquisition.parcel_id
                continue
            land_acquisition.name = "%s > %s" % (land_acquisition.parcel_id, land_acquisition.address)

    @api.depends('purchase_price', 'sold_price')
    def _compute_profit_margin(self):
        for land_acquisition in self:
            land_acquisition.profit_margin = land_acquisition.sold_price - land_acquisition.purchase_price
