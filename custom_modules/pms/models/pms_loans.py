from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime
from odoo.fields import Command
from datetime import date

# Agrupar por fase
# Ordenar de mayor a menor el available balance

class pms_loans(models.Model):
    _name = "pms.loans"
    _description = "Table for loans"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'documents.mixin']

    name = fields.Char(string="Loan Number")
    lender = fields.Many2one("res.partner", string="Lender")
    loan_amount = fields.Monetary(string="Loan Amount", currency_field='company_currency_id')
    maturity_date = fields.Date(string="Maturity Date", tracking=True)
    loan_type = fields.Selection(selection=[("construction", "Construction"), ("rent", "Rent")], required=True, string="Type of Loan")
    interest = fields.Float(string="Interest Rate")
    exit_status = fields.Selection(selection=[("ongoing", "Process"), ("extended", "Extended"), ("refinanced", "Refinanced"), ("sold", "Sold")], string="Exit Status", default="ongoing", tracking=True)
    extension_count = fields.Integer(string="Number of Extensions", default = 0)
    property_address = fields.Many2one("pms.property", string="Property Address")
    monthly_payment = fields.Monetary(string="Mortgage Payment", currency_field='company_currency_id')
    draw_history = fields.One2many("pms.draws", "loan_id")
    project_phase = fields.Selection(selection=[
        ("pending", "Pending"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("epp", "EPP"),
        ("pip", "PIP"),
        ("pps", "PPS"),
        ("ppa", "PPA"),
        ("cop", "COP"),
        ("cop1", "COP1"),
        ("cop2", "COP2"),
        ("cop3", "COP3"),
        ("cop4", "COP4"),
        ("coc", "COC"),
        ("completed", "Completed"),
        ], compute="_compute_project_phase", string="Project Phase", readonly=True, store=True)   
    loan_payment_type = fields.Selection(selection=[("30_years_fixed", "30 Years Fixed"), ("interest_only", "Interest Only")], string="Type of Loan Payment")

    days_to_expire_loan = fields.Float(string="Days to expire", compute="_days_to_expire_loan", store=True)

    available_balance = fields.Monetary(string="Available Balance", currency_field='company_currency_id', compute="_calculate_balance", store=True)
    total_drawed_amount = fields.Monetary(string="Drawed Amount", currency_field='company_currency_id', compute="_calculate_balance", store=False)
    draw_item = fields.One2many("pms.draw.items", "loan_id", string="Draw Items")
    
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
    
    # Control Fields
    
    servicing_company = fields.Many2one("res.partner", string="Servicing Company", readonly=False)
        #  abajo de project phase many2one con contacts?
    servicing_loan_number = fields.Char(string="Servicing Loan Number", readonly=False)
    #  char, unique, que avise
 
    first_mortgage_payment_date = fields.Date(string="First Mortgage Payment Date", readonly=False)
    #  manual, date, debajo de mortgage_payment
 
    extension_requested = fields.Boolean(string="Extension Requested", default=False, readonly=False)
    #  control boolean, manualmente, al final
    refinancing_process_check = fields.Boolean(string="Refinancing Process", default=False, readonly=False)
    #  manual, boolean
    
    max_date_to_pay = fields.Integer(string="Max Date to Pay", readonly=False)


    # RENT DASHBOARD FIELDS
    
    # MAKE READONLY FALSE IF loan_type IS "RENT"
    computed_loan_balance = fields.Float(
        string='Computed Loan Balance',
        compute='_compute_loan_balance',
        store=True,
        readonly=True,
    )
    manual_loan_balance = fields.Monetary(string="Manual Loan Balance", currency_field='company_currency_id', readonly=False)
    loan_balance = fields.Monetary(string="Loan Balance", currency_field='company_currency_id', readonly=True, compute="_compute_loan_balance_display", store=True)

    def _calculate_balance(self):
        for record in self:
            drawed_amount = record.env["pms.draws"].sudo().search([("loan_id", "=", record.id)])
            drawed_amount = sum(drawed_amount.sudo().mapped("draw_amount"))

            record.total_drawed_amount = drawed_amount

            record.available_balance = record.loan_amount - record.total_drawed_amount

    @api.depends('property_address')
    def _compute_loan_balance(self):
        for record in self:
            if record.property_address and record.loan_type == "rent":
                loan_tag = record.env['account.account.tag'].search([('name', '=', 'Loan Financial Institution')], limit=1)
                if loan_tag:
                    analytic_items = record.env['account.analytic.line'].search([
                        ('account_id', '=', record.property_address.analytical_account.id),
                        ('general_account_id.tag_ids', 'in', loan_tag.ids),
                    ])
                
                    if analytic_items:
                        total_balance = sum(analytic_items.mapped('amount'))
                        record.computed_loan_balance = total_balance
                    else:
                        record.computed_loan_balance = 1
                else:
                    record.computed_loan_balance = 2
            else:
                record.computed_loan_balance = 3
                        
    @api.depends('loan_type', 'computed_loan_balance', 'manual_loan_balance')
    def _compute_loan_balance_display(self):
        for record in self:
            if record.loan_type == 'rent':
                record.loan_balance = record.computed_loan_balance
            else:
                record.loan_balance = record.manual_loan_balance
                    
    _sql_constraints = [
        ('ref_unique', 'unique(servicing_loan_number)', 'Servicing Loan Number should be unique.'),
    ]

    @api.depends("property_address")
    def _compute_project_phase(self):
        for record in self:
            projects = record.env["pms.projects"].search([("address", "=", record.property_address.id)]).ids
            if projects:
                project = record.env["pms.projects"].browse(projects[0])
                record.project_phase = project.status_construction
            else:
                record.project_phase = "pending"


    @api.onchange("max_date_to_pay")
    def check_max_date(self):
        if self.max_date_to_pay < 1:
            self.max_date_to_pay = False
            self.env['update.owner.call.day'].simple_notification("error", "Error", "Date cannot be negative.", False)
        if self.max_date_to_pay > 31:
            self.max_date_to_pay = False
            self.env['update.owner.call.day'].simple_notification("error", "Error", "Date cannot be greater than the number of days in a month.", False)

    def extend_loan(self):
        self.extension_count = self.extension_count + 1
        self.exit_status = "extended"

    def refinanced(self):
        self.exit_status = "refinanced"

    def sold(self):
        self.exit_status = "sold"

    def create_draw_items(self):
        for record in self:
            if record.loan_type == "construction":
                record.draw_item = [(0, 0, {"draw_step": "permits_plan", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "demolition_dumpsters", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "slab", "budget": 0,"loan_id": record.id}),
                                    (0, 0, {"draw_step": "foundation", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "framing", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "plumbing_finish", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "plumbing_rough", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "electrical_finish", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "elect_rough", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "metal_works", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "vanity_mirrors", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "hvac", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "roof", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "pressure_wash", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "insulation", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "drywall_tapeing", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "tile_finish", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "tile_install", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "doors_windows", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "finish_carpentry", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "paint_specialties", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "windows", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "flooring", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "stairs", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "outdoor_patio", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "hardware", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "pool", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "appliances", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "countertops", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "kitchen_cabinets", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "general_labor", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "landscaping", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "hardscape_driveway", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "bathrooms", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "fence", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "pm_fee", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "open_item", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "open_item2", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "open_item3", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "staging_cleanup", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "contingency", "budget": 0, "loan_id": record.id}),
                                    (0, 0, {"draw_step": "owner_contribution", "budget": 0, "loan_id": record.id}),]
            else:
                raise ValidationError("Loan type is not valid")

    # === Computed Fields === #
    @api.depends("maturity_date")
    def _days_to_expire_loan(self):
        for record in self:
            if record.maturity_date:
                timedelta = record.maturity_date - datetime.today().date()
                record.days_to_expire_loan = timedelta.days + float(timedelta.seconds) / 86400
            else:
                record.days_to_expire_loan = 0