from odoo import models, fields, _, api, tools

from datetime import date
from dateutil.relativedelta import relativedelta

import logging
_logger = logging.getLogger(__name__)

class property_timeline_report(models.Model):
    _name = "pms.property.loan.report"
    _description = "Property Loan Report"
    _auto = False
    
    property_id = fields.Many2one("pms.property", string="Property", readonly=True)
    property_owner = fields.Many2one("res.partner", string="Property Owner", readonly=True)
    # observations = fields.Char(string="Observations", readonly=False)
    
    # PMS Loans
    lender = fields.Many2one("res.partner", readonly=True)
    maturity_date = fields.Date(string="Maturity Date", readonly=True)
    project_phase = fields.Selection(string="Project Phase", readonly=True, selection=[
        ("pending", "Pending"), ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"), ("pip", "PIP"), ("pps", "PPS"),
        ("ppa", "PPA"), ("cop", "COP"), ("cop1", "COP1"), ("cop2", "COP2"), ("cop3", "COP3"), ("cop4", "COP4"), ("cop5", "COP5"),
        ("coc", "COC"), ("completed", "Completed")
    ])
    interest_rate = fields.Float(string="Interest Rate", readonly=True)
    loan_type = fields.Selection(selection=[("construction", "Construction"), ("rent", "Rent")], readonly=True, string="Type of Loan")
    exit_status = fields.Selection(selection=[("ongoing", "Process"), ("extended", "Extended"), ("refinanced", "Refinanced"), ("sold", "Sold")], string="Exit Status", readonly=True)
    # New pms.loans fields
    servicing_company = fields.Many2one("res.partner", string="Servicing Company", readonly=True)
    servicing_loan_number = fields.Char(string="Servicing Loan Number", readonly=True)
    first_mortgage_payment_date = fields.Date(string="First Mortgage Payment Date", readonly=True)
    extension_requested = fields.Boolean(string="Extension Requested", default=True, readonly=True)
    refinancing_process_check = fields.Boolean(string="Refinancing Process", default=True, readonly=True)
    max_date_to_pay = fields.Integer(string="Max Date to Pay", readonly=True)
    
    # PMS TRANSACTIONS
    
    transaction_type = fields.Selection([
            ('sale', "Sale"),
            ('purchase', "Purchase"),
            ('refinance', "Refinance")
        ], string="Transaction Type", readonly=True)
    
    # Boolean controls
    matched_payment = fields.Boolean(string="Matched?", readonly=True)
    mortgage_payment = fields.Boolean(string="Mortgage Payment", readonly=True)
    
    
    @property
    def _table_query(self):
        year = self.env.context.get('year')
        month = self.env.context.get('month')
        
        if year and month:
            start_date = date(year, month, 1)
            end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)
            two_months_ago = start_date - relativedelta(months=2)
        else:
            today = date.today()
            start_date = date(today.year, today.month, 1)
            end_date = (start_date + relativedelta(months=1)) - relativedelta(days=1)
            two_months_ago = start_date - relativedelta(months=2)
    
        return f"""
            SELECT
                pp.id AS id,
                pp.id AS property_id,
                pp.partner_id AS property_owner,
                pl.maturity_date AS maturity_date,
                pl.lender AS lender,
                pl.interest AS interest_rate,
                pl.loan_type AS loan_type,
                pl.exit_status AS exit_status,
                pp.utility_phase AS project_phase,
                pl.servicing_company AS servicing_company,
                pl.servicing_loan_number AS servicing_loan_number,
                pl.first_mortgage_payment_date AS first_mortgage_payment_date,
                pl.extension_requested AS extension_requested,
                pl.refinancing_process_check AS refinancing_process_check,
                pl.max_date_to_pay AS max_date_to_pay,
                pt.transaction_type AS transaction_type,
                sub2.mortgage_payment AS mortgage_payment,
                sub2.matched_payment AS matched_payment

                FROM pms_property AS pp
                LEFT JOIN pms_loans AS pl ON pp.id = pl.property_address
                LEFT JOIN (
                    SELECT
                        property_address,
                        transaction_type
                    FROM pms_transactions
                    WHERE transaction_date BETWEEN '{two_months_ago}' AND '{start_date}'
                ) AS pt ON pp.id = pt.property_address

                LEFT JOIN (
                    SELECT
                        true AS mortgage_payment,
                        sub3.match_payment AS matched_payment,
                        sub1.address AS address,
                        sub1.move_id AS move_id
                    FROM (
                        SELECT
                            aml.move_id AS move_id,
                            pp2.id AS address
                        FROM account_analytic_line AS aal
                        INNER JOIN pms_property AS pp2 ON aal.account_id = pp2.analytical_account
                        INNER JOIN account_account AS aa ON aal.general_account_id = aa.id
                        INNER JOIN account_move_line AS aml ON aal.move_line_id = aml.id
                        WHERE aal.date BETWEEN '{start_date}' AND '{end_date}'
                        AND aa.code = '6510007'
                        AND aml.parent_state = 'posted'
                        GROUP BY aml.move_id, pp2.id
                    ) sub1
                    LEFT JOIN (
                        SELECT
                            true AS match_payment,
                            aml.move_id AS move_id

                        FROM account_move_line AS aml
                        INNER JOIN account_account AS aa ON aml.account_id = aa.id

                        WHERE aa.account_type = 'asset_cash' OR (aa.name ILIKE '%%outstanding%%' AND aml.matching_number IS NOT NULL)
                        GROUP BY aml.move_id
                    ) sub3 ON sub1.move_id = sub3.move_id 
                ) sub2 ON pp.id = sub2.address

            WHERE pp.own_third = 'own'
            AND pl.maturity_date >= '{start_date}'
        """
                # (CASE
                #     WHEN loan_report.mortgage_payment AND EXISTS (
                #         SELECT 1
                #         FROM account_analytic_line AS aal
                #         INNER JOIN pms_property AS pp2 ON aal.account_id = pp2.analytical_account
                #         INNER JOIN pms_loans AS pl_aal ON pp2.id = pl_aal.property_address
                #         INNER JOIN account_account AS aa ON aal.general_account_id = aa.id
                #         -- LEFT JOIN account_payment_method_line AS apml ON aa.id = apml.payment_account_id
                #         -- LEFT JOIN account_journal AS aj ON apml.journal_id = aj.id
                #         INNER JOIN account_move_line AS aml ON aal.move_line_id = aml.move_id
                #         WHERE aal.date BETWEEN '{start_date}' AND '{end_date}'
                #         AND pl_aal.property_address = loan_report.property_id
                #         AND (
                #             aa.account_type = 'asset_cash'
                #             OR (
                #                 aa.name ILIKE 'Outstanding'
                #                 -- aa.code = '6510007'
                #                 AND aml.matching_number IS NOT NULL
                #                 )
                #             )
                #         ) THEN TRUE
                #     ELSE FALSE
                # END) AS matched_payment

                    # ( CASE WHEN EXISTS (
                    #         SELECT 1
                    #         FROM account_analytic_line AS aal
                    #         INNER JOIN pms_property AS pp2 ON aal.account_id = pp2.analytical_account
                    #         INNER JOIN pms_loans AS pl_aal ON pp2.id = pl_aal.property_address
                    #         INNER JOIN account_account AS aa ON aal.general_account_id = aa.id
                    #         WHERE aal.date BETWEEN '{start_date}' AND '{end_date}'
                    #         AND pl_aal.property_address = pp.id
                    #         AND aa.code = '6510007'
                    #     ) THEN TRUE ELSE FALSE END
                    # ) AS mortgage_payment


#                 -- first it checks if mortgage_payment is true or false
#                 -- if true it continues to check if there is matched payment
#                 -- if mortgage_payment is false, then matched_payment is false
                

                
#                 -- los registros de mortgage payment, ver asiento completo (Account_move y account_move_line), buscar lo de 'asset_cash' 
#                 -- or that aal.general_account_id includes "Outstanding", tendremos el asiento que encontramos, la linea tiene asset_cash
#                 -- o las lineas de outstanding, si tiene asset_cash entonces true, y si no, revisar que la linea de outstanding tengan matched number



                    # WHEN mortgage_payment = TRUE AND EXISTS (
                    #     SELECT 1
                    #     FROM account_analytic_line AS aal
                    #     INNER JOIN pms_property AS pp2 ON aal.account_id = pp2.analytical_account
                    #     INNER JOIN pms_loans AS pl_aal ON pp2.id = pl_aal.property_address
                    #     INNER JOIN account_account AS aa ON aal.account_id = aa.id
                    #     INNER JOIN account_payment_method_line AS apml ON aa.id = apml.payment_account_id
                    #     INNER JOIN account_journal AS aj ON apml.journal_id = aj.id
                    #     WHERE aal.date BETWEEN '{start_date}' AND '{end_date}'
                    #     AND pl_aal.property_address = loan_report.property_id
                    #     AND (aa.account_type = 'asset_cash' OR aa.id = apml.payment_account_id)
                    #     AND aj.type = 'bank'

                    # ) THEN TRUE ELSE FALSE


# pms_loans.property_address = pms_property.id
# pms_property.analytical_account =  account_analytic_line.account_id
# Filter the start_date monthwere using
# filter by specific account to only returing mortgage records --> check if pms_loans.monthly_payment exists?
# if the record is within the date and has the mortgage records then mortgage_payment = True

# dos campos Boolean si esta matched y lo otro de mortgage
# despues esta tabla nueva hacerle un join con tabla de account_move y move_line, 
# para poder buscar el asiento/registro de este mes si esta matched con un banco, si esta ponemos una fecha de pago, y asi, 


class select_property_loan_report_wizard(models.TransientModel):
    _name = 'select.property.loan.report.wizard'
    _description = 'Select Property Loan Report Wizard'
    
    month = fields.Selection(string="Month", default=str(date.today().month), selection = [
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'), ('5', 'May'),
        ('6', 'June'), ('7', 'July'), ('8', 'August'), ('9', 'September'), ('10', 'October'),
        ('11', 'November'), ('12', 'December')])    
    
    year = fields.Integer(string="Year", default=lambda self: fields.Date.today().year)
    
    def open_report(self):
        
        tree_view = self.env.ref('pms.view_property_loan_report_tree')
        
        if self.month and self.year:
            return {
                'name': 'Property Loan Report',
                'type': 'ir.actions.act_window',
                'res_model': 'pms.property.loan.report',
                'view_mode': 'tree',
                'view_id': tree_view.id,
                'target': 'current',
                'context': {
                    'month': int(self.month),
                    'year': self.year
                }
            }