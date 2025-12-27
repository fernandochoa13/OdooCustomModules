from odoo import api, models, fields
from odoo.tools.misc import formatLang

from datetime import date
from dateutil.relativedelta import relativedelta

class pms_rent_report(models.Model):
    _name = 'pms.rent.report'
    _description = 'Rent Report'
    _auto = False
    
    # REPORT FIELDS
    id = fields.Integer(string='ID', readonly=True)
    
    lender = fields.Many2one("res.partner", string="Lender", readonly=True)
    portfolio = fields.Many2one('pms.portfolio', string='Portfolio', readonly=True)
    portfolio_color = fields.Char(string="Portfolio Color", readonly=True)
    arv = fields.Float(string="ARV") # CHOOSE BETWEEN PMS PORTFOLIO AND PMS PROPERTY
    
    # PMS LOANS FIELDS
    loan_number = fields.Char(string="Loan Number", readonly=True) # sacar de pms.loans
    interest = fields.Float(string="Interest Rate", readonly=True) # sacar de pms.loans
    loan_balance = fields.Float(string="Loan Balance", readonly=True)
    
    # PMS PROPERTY FIELDS
    property_owner = fields.Many2one("res.partner", string="Owner of property", readonly=True) 
    property_address = fields.Many2one("pms.property", string="Property Address", readonly=True)
    status_house = fields.Selection(
        selection=[
            ('draft', "Draft"),
            ('construction', "Construction"),
            ('coc', "COC"),
            ('rented', "Rented"),
            ('sold', "Sold"),
            ('repair', "Repair"),
        ],
        string="Status")
 
    
    # PMS UNITS FIELDS
    unit = fields.Char(string='Unit', readonly=True)
    unit_status = fields.Selection([('occupied', 'Occupied'), ('vacant', 'Vacant'), ('eviction', 'Eeviction')], string='Property Status', readonly=True)
    rent = fields.Float(string='Rent', readonly=True)
    
    # ACCOUNT MOVE LINE FIELDS
    mortgage = fields.Float(string='Mortgage', readonly=True)
    
    repairs = fields.Float(string='Repairs', readonly=True)
    utilities = fields.Float(string='Utilities', readonly=True, help="Utilities costs for the property")
    taxes = fields.Float(string='Taxes', readonly=True, help="Property taxes costs")
    insurance = fields.Float(string='Insurance', readonly=True, help="Property insurance costs")
    hoa = fields.Float(string='HOA', readonly=True, help="Homeowners Association fees")
    services = fields.Float(string='Services', readonly=True, help="Other services costs for the property")
    turnover = fields.Float(string='Turnover', readonly=True)
    
    # CALCULATED FIELDS
    
    profit = fields.Float(
        string='Profit',
        readonly=True,
        compute='_compute_profit',
        help="Profit = Rent - Mortgage"
    )
    def _compute_profit(self):
        for record in self:
            record.profit = record.rent - record.mortgage

    cashflow = fields.Float(
        string='Cashflow',
        readonly=True,
        compute='_compute_cashflow',
        help="Cashflow = Profit - Repairs - Turnovers"
    )
    def _compute_cashflow(self):
        for record in self:
            record.cashflow = record.profit - record.repairs - record.turnover

    equity_refinance = fields.Float(
        string='Equity Refinance',
        readonly=True,
        compute='_compute_equity_refinance',
        help="Equity Refinance = (ARV * 67%) - Loan Balance"
    )
    def _compute_equity_refinance(self):
        for record in self:
            record.equity_refinance = record.arv * 0.67 - abs(record.loan_balance)

    net_worth = fields.Float(
        string='Net Worth',
        readonly=True,
        compute='_compute_net_worth',
        help="Net Worth = ARV - Equity Refinance"
    )
    def _compute_net_worth(self):
        for record in self:
            record.net_worth = record.arv - abs(record.equity_refinance)
    
    # HTML FIELDS
    
    property_address_html = fields.Html(string='Property Address (HTML)', readonly=True, compute='_compute_property_address_html')
    
    def _compute_property_address_html(self):
        for record in self:
            record.property_address_html = f"""
                <div style="font-weight: bold; margin-top:-6px; padding: 6px 0 7px 0; margin: -6px 0 -6px 0; background-color: {record.portfolio_color if record.portfolio_color else "" };">
                    {record.property_address.name}
                </div>
            """
    
    @property
    def _table_query(self):
        year = self.env.context.get('year')
        month = self.env.context.get('month')
        
        if year and month:
            start_date = date(year, month, 1)
            end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)
        else:
            today = date.today()
            start_date = date(today.year, today.month, 1)
            end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)
    
        return f"""
        WITH PropertyUnitCounts AS (
                SELECT
                    property_address,
                    COUNT(id) AS unit_count
                FROM pms_units
                GROUP BY property_address
            )
            SELECT
                pu.id AS id,
                pp.id AS property_address,
                pp.status_property AS status_house,
                pu.name AS unit,
                pu.id AS unit_id,
                pu.status AS unit_status,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(pl.loan_balance) / MAX(puc.unit_count)
                    ELSE MAX(pl.loan_balance)
                END AS loan_balance,
                MAX(pl.lender) AS lender,
                MAX(pl.loan_number) AS loan_number,
                MAX(pl.interest) AS interest,
                ppo.id AS portfolio,
                ppo.color AS portfolio_color,
                pp.partner_id AS property_owner,
                MAX(pu.rent) AS rent,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.repairs) / MAX(puc.unit_count)
                    ELSE MAX(aal.repairs)
                END AS repairs,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.utilities) / MAX(puc.unit_count)
                    ELSE MAX(aal.utilities)
                END AS utilities,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.taxes) / MAX(puc.unit_count)
                    ELSE MAX(aal.taxes)
                END AS taxes,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.insurance) / MAX(puc.unit_count)
                    ELSE MAX(aal.insurance)
                END AS insurance,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.hoa) / MAX(puc.unit_count)
                    ELSE MAX(aal.hoa)
                END AS hoa,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.services) / MAX(puc.unit_count)
                    ELSE MAX(aal.services)
                END AS services,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aal.turnover) / MAX(puc.unit_count)
                    ELSE MAX(aal.turnover)
                END AS turnover,
                CASE
                    WHEN MAX(aalm.mortgage) > 10000 THEN 0
                    WHEN MAX(puc.unit_count) > 0 THEN MAX(aalm.mortgage) / MAX(puc.unit_count)
                    ELSE MAX(aalm.mortgage)
                END AS mortgage,
                CASE
                    WHEN MAX(puc.unit_count) > 0 THEN
                        CASE
                            WHEN ppo.id IS NULL THEN MAX(pp.arv) / MAX(puc.unit_count)
                            ELSE MAX(ppo.arv) / MAX(puc.unit_count)
                        END
                    ELSE
                        CASE
                            WHEN ppo.id IS NULL THEN MAX(pp.arv)
                            ELSE MAX(ppo.arv)
                        END
                END AS arv
            FROM pms_property pp
            INNER JOIN pms_units pu ON pp.id = pu.property_address
            LEFT JOIN PropertyUnitCounts puc ON pp.id = puc.property_address
            LEFT JOIN (
                SELECT
                    pl.property_address AS property_address,
                    pl.name AS loan_number,
                    pl.lender AS lender,
                    pl.interest AS interest,
                    pl.loan_balance AS loan_balance
                FROM pms_loans pl
                WHERE pl.loan_type = 'rent'
                AND (pl.exit_status != 'refinanced' AND pl.exit_status != 'sold')
            ) pl ON pp.id = pl.property_address
            LEFT JOIN pms_portfolio ppo ON pp.portfolio = ppo.id
            LEFT JOIN (
                SELECT
                    aal.account_id,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'Repairs') AS repairs,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'Utilities') AS utilities,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'Taxes') AS taxes,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'Insurance') AS insurance,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'HOA') AS hoa,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'Services') AS services,
                    SUM(aml.balance) FILTER (WHERE aat.name = 'Turnover') AS turnover
                FROM account_analytic_line aal
                INNER JOIN account_move_line aml ON aal.move_line_id = aml.id
                INNER JOIN account_account aa ON aal.general_account_id = aa.id
                INNER JOIN account_account_account_tag tagrel ON aa.id = tagrel.account_account_id
                INNER JOIN account_account_tag aat ON tagrel.account_account_tag_id = aat.id
                WHERE aal.date BETWEEN '{start_date}' AND '{end_date}'
                    AND aat.name IN ('Repairs', 'Utilities', 'Taxes', 'Insurance', 'HOA', 'Services', 'Turnover')
                GROUP BY aal.account_id
            ) aal ON pp.analytical_account = aal.account_id
            LEFT JOIN (
                SELECT
                    aal.account_id as account_id,
                    SUM(amll.credit) as mortgage
                FROM account_analytic_line aal
                INNER JOIN account_move_line aml ON aal.move_line_id = aml.id
                INNER JOIN account_move_line amll ON amll.move_id = aml.move_id
                INNER JOIN account_account aa ON aal.general_account_id = aa.id
                INNER JOIN account_account_account_tag tagrel ON aa.id = tagrel.account_account_id
                INNER JOIN account_account_tag aat ON tagrel.account_account_tag_id = aat.id
                WHERE aal.date BETWEEN '{start_date}' AND '{end_date}'
                    AND aat.name = 'Mortgage'
                GROUP BY aal.account_id
            ) aalm ON pp.analytical_account = aalm.account_id
            WHERE (pp.status_property = 'rented' OR pp.status_property = 'coc' OR pp.available_for_rent = true)
              AND pp.own_third = 'own'
            GROUP BY pp.id, pu.name, pu.id, pu.status, ppo.id, ppo.color, pp.partner_id, pp.status_property
        """
    
    
    
    class select_rent_report_wizard(models.TransientModel):
        _name = 'select.rent.report.wizard'
        _description = 'Select Rent Report Wizard'
        
        month = fields.Selection(string="Month", default=str(date.today().month - 1), selection = [
            ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'),
            ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'),
            ('11', 'November'), ('12', 'December')])    
        
        year = fields.Integer(string="Year", default=lambda self: fields.Date.today().year)
        
        def open_report(self):
            month_name = dict(self._fields['month'].selection).get(self.month)
            tree_view = self.env.ref('pms.view_rent_report_tree')
            
            if self.month and self.year:
                return {
                    'name': f'Rent Report: {month_name}, {self.year}',
                    'type': 'ir.actions.act_window',
                    'res_model': 'pms.rent.report',
                    'view_mode': 'tree',
                    'view_id': tree_view.id,
                    'target': 'current',
                    'context': {
                        'month': int(self.month),
                        'year': self.year
                    }
                }
