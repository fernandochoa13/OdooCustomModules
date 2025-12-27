from collections import defaultdict
from contextlib import ExitStack, contextmanager
from datetime import date, timedelta
from hashlib import sha256
from json import dumps
import re
from textwrap import shorten
from unittest.mock import patch

from odoo import api, fields, models, _, Command, tools
from odoo.addons.base.models.decimal_precision import DecimalPrecision
# from odoo.addons.account.tools import format_rf_reference

from odoo import models, fields, tools

from odoo import models, fields, tools

class DrawsReport(models.Model):
    _name = "draws.report"
    _description = "Draws Report"
    _auto = False

    id = fields.Integer(readonly=True)
    loan_number = fields.Char(string='Loan Number', readonly=True)
    lender = fields.Char(string='Lender', readonly=True)
    loan_amount = fields.Float(string='Loan Amount', readonly=True)
    available_balance = fields.Float(string='Available Loan Balance', readonly=True)
    property_address = fields.Char(string='Property Address', readonly=True)
    project_phase = fields.Char(string='Project Phase', readonly=True)
    maturity_date = fields.Date(string='Maturity Date', readonly=True)
    loan_type = fields.Char(string='Loan Type', readonly=True)
    interest_rate = fields.Float(string='Interest Rate', readonly=True)
    exit_status = fields.Char(string='Exit Status', readonly=True)
    extensions = fields.Integer(string='Extensions', readonly=True)
    mortgage_payment = fields.Float(string='Mortgage Payment', readonly=True)
    days_expired = fields.Integer(string='Days Expired', readonly=True)
    first_draw_date = fields.Date(string='Draw #1 Date', readonly=True)
    first_draw_amount = fields.Float(string='Draw #1 Amount', readonly=True)
    second_draw_date = fields.Date(string='Draw #2 Date', readonly=True)
    second_draw_amount = fields.Float(string='Draw #2 Amount', readonly=True)
    third_draw_date = fields.Date(string='Draw #3 Date', readonly=True)
    third_draw_amount = fields.Float(string='Draw #3 Amount', readonly=True)
    fourth_draw_date = fields.Date(string='Draw #4 Date', readonly=True)
    fourth_draw_amount = fields.Float(string='Draw #4 Amount', readonly=True)
    fifth_draw_date = fields.Date(string='Draw #5 Date', readonly=True)
    fifth_draw_amount = fields.Float(string='Draw #5 Amount', readonly=True)

    @property
    def _table_query(self):
        return f"""
                SELECT
                pl.id AS id,
                pl.name AS loan_number,
                rp.name AS lender,
                pl.loan_amount AS loan_amount,
                pp.name AS property_address,
                pl.maturity_date AS maturity_date,
                pl.loan_type AS loan_type,
                pl.interest AS interest_rate,
                pl.exit_status AS exit_status,
                pl.extension_count AS extensions,
                pl.monthly_payment AS mortgage_payment,
                pl.days_to_expire_loan AS days_expired,
                
                pl.loan_amount - COALESCE((
                    SELECT SUM(pdl.amount_drawed)
                    FROM pms_draw_lines pdl
                    INNER JOIN pms_draws pd ON pdl.draw_id = pd.id
                    WHERE pd.loan_id = pl.id
                ), 0) AS available_balance,

                -- Draw #1
                (SELECT pd.date FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1) AS first_draw_date,
                (SELECT SUM(pdl.amount_drawed) FROM pms_draw_lines pdl WHERE pdl.draw_id = (SELECT pd.id FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1)) AS first_draw_amount,

                -- Draw #2
                (SELECT pd.date FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 1) AS second_draw_date,
                (SELECT SUM(pdl.amount_drawed) FROM pms_draw_lines pdl WHERE pdl.draw_id = (SELECT pd.id FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 1)) AS second_draw_amount,

                -- Draw #3
                (SELECT pd.date FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 2) AS third_draw_date,
                (SELECT SUM(pdl.amount_drawed) FROM pms_draw_lines pdl WHERE pdl.draw_id = (SELECT pd.id FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 2)) AS third_draw_amount,

                -- Draw #4
                (SELECT pd.date FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 3) AS fourth_draw_date,
                (SELECT SUM(pdl.amount_drawed) FROM pms_draw_lines pdl WHERE pdl.draw_id = (SELECT pd.id FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 3)) AS fourth_draw_amount,

                -- Draw #5
                (SELECT pd.date FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 4) AS fifth_draw_date,
                (SELECT SUM(pdl.amount_drawed) FROM pms_draw_lines pdl WHERE pdl.draw_id = (SELECT pd.id FROM pms_draws pd WHERE pd.loan_id = pl.id ORDER BY pd.date LIMIT 1 OFFSET 4)) AS fifth_draw_amount

                FROM
                    pms_loans pl
                LEFT JOIN
                    pms_property pp ON pp.id = pl.property_address
                LEFT JOIN 
                    res_partner rp ON rp.id = pl.lender
        """


