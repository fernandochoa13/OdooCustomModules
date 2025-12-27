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

class DuplicateAccountMoveReference(models.Model):
    _name = "duplicate.reference"
    _description = "Possible Duplicate Bills Report"
    _auto = False
    _order = 'numeric_reference, id'

    id = fields.Integer(readonly=True)
    move_name = fields.Char(string='Move Name', readonly=True)
    bill_date = fields.Date(string='Bill Date', readonly=True)
    product_inv = fields.Char(string='Product', readonly=True)
    partner_name = fields.Char(string='Vendor', readonly=True)
    analytic_accounts = fields.Char(string='Analytic Accounts', readonly=True)
    checked_duplicate = fields.Boolean(string='Checked Duplicate', readonly=True)
    reference = fields.Char(string='Reference', readonly=True)
    payment_reference = fields.Char(string='Payment Reference', readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)
    numeric_reference = fields.Char(string='Numeric Reference', readonly=True)

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
                SELECT
                    am.id AS id,
                    am.name AS move_name,
                    am.invoice_date AS bill_date,
                    (
                        SELECT STRING_AGG(DISTINCT COALESCE(pt.name->>'en_US', pt.name::text), ',')
                        FROM account_move_line AS aml
                        INNER JOIN product_product AS pp ON aml.product_id = pp.id
                        INNER JOIN product_template AS pt ON pp.product_tmpl_id = pt.id
                        WHERE aml.move_id = am.id
                    ) AS product_inv,
                    am.partner_id AS partner_id,
                    rp.name AS partner_name,
                    am.analytic_accounts AS analytic_accounts,
                    am.checked_duplicate AS checked_duplicate,
                    am.ref AS reference,
                    am.payment_reference AS payment_reference,
                    am.amount_total AS total_amount,
                    dup.numeric_reference AS numeric_reference
                FROM account_move am
                JOIN (
                    SELECT
                        COALESCE(
                            REGEXP_REPLACE(ref, '[^0-9]', '', 'g'),
                            REGEXP_REPLACE(payment_reference, '[^0-9]', '', 'g')
                        ) AS numeric_reference,
                        COUNT(*) as cnt
                    FROM account_move
                    WHERE move_type = 'in_invoice' AND state != 'cancel'
                    GROUP BY
                        COALESCE(
                            REGEXP_REPLACE(ref, '[^0-9]', '', 'g'),
                            REGEXP_REPLACE(payment_reference, '[^0-9]', '', 'g')
                        )
                    HAVING
                        COUNT(*) > 1
                ) dup
                ON COALESCE(
                    REGEXP_REPLACE(am.ref, '[^0-9]', '', 'g'),
                    REGEXP_REPLACE(am.payment_reference, '[^0-9]', '', 'g')
                ) = dup.numeric_reference
                LEFT JOIN res_partner rp ON am.partner_id = rp.id
                WHERE am.move_type = 'in_invoice' AND am.state != 'cancel'
                ORDER BY dup.numeric_reference, am.id
        """
