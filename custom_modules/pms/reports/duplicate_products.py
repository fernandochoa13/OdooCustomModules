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

class DuplicateAccountMoveProducts(models.Model):
    _name = "duplicate.products"
    _description = "Possible Duplicate Bills Report"
    _auto = False
    _order = 'product_inv asc, partner_name asc, analytic_accounts asc' 

    id = fields.Integer(readonly=True)
    move_name = fields.Char(string='Move Name', readonly=True)
    bill_date = fields.Date(string='Bill Date', readonly=True)
    product_inv = fields.Char(string='Product', readonly=True)
    partner_name = fields.Char(string='Vendor', readonly=True)
    analytic_accounts = fields.Char(string='Analytic Accounts', readonly=True)
    checked_duplicate = fields.Boolean(string='Checked Duplicate', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)

    def check_duplicate(self):
        self.ensure_one()
        self.env['account.move'].browse(self.id).write({'checked_duplicate': True})

    def check_duplicate_all(self):
        move_ids = self.mapped('id')
        self.env['account.move'].browse(move_ids).write({'checked_duplicate': True})

    def uncheck_duplicate_all(self):
        move_ids = self.mapped('id')
        self.env['account.move'].browse(move_ids).write({'checked_duplicate': False})

    def open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    @property
    def _table_query(self):
        return """
            WITH ProductInvoices AS (
                SELECT
                    am.id AS move_id,
                    STRING_AGG(DISTINCT COALESCE(pt.name->>'en_US', pt.name::text), ',') AS product_inv
                FROM account_move am
                JOIN account_move_line aml ON am.id = aml.move_id
                JOIN product_product pp ON aml.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                WHERE am.move_type = 'in_invoice' AND am.state != 'cancel'
                GROUP BY am.id
            ),
            DuplicateInvoices AS (
                SELECT
                    pi.product_inv,
                    am.partner_id,
                    am.analytic_accounts,
                    COUNT(*) as cnt
                FROM account_move am
                JOIN ProductInvoices pi ON am.id = pi.move_id
                WHERE am.move_type = 'in_invoice' AND am.state != 'cancel'
                GROUP BY pi.product_inv, am.partner_id, am.analytic_accounts
                HAVING COUNT(*) > 1
            )
            SELECT
                MIN(am.id) AS id,
                pi.product_inv,
                am.partner_id AS partner_id,
                rp.name AS partner_name,
                am.analytic_accounts AS analytic_accounts,
                am.checked_duplicate AS checked_duplicate,
                am.name AS move_name,
                am.invoice_date AS bill_date,
                am.ref AS reference,
                am.amount_total AS total_amount
            FROM account_move am
            JOIN ProductInvoices pi ON am.id = pi.move_id
            JOIN DuplicateInvoices dup ON pi.product_inv = dup.product_inv
                AND am.partner_id = dup.partner_id
                AND am.analytic_accounts = dup.analytic_accounts
            LEFT JOIN res_partner rp ON am.partner_id = rp.id
            WHERE am.move_type = 'in_invoice' 
                AND am.state != 'cancel'
            GROUP BY pi.product_inv, am.partner_id, rp.name, am.analytic_accounts, am.checked_duplicate, am.name, am.invoice_date, am.ref, am.amount_total
        """
