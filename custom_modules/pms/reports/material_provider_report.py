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


class MatProviderReport(models.Model):
    _name = "provider.report"
    _description = "Material Provider Report"
    _auto = False

    id = fields.Integer('ID', readonly=True)
    provider_name = fields.Char('Provider', readonly=True)
    pct_rejection = fields.Float('Rejection %', readonly=True)
    average_rejection_per_order = fields.Float('Average Rejections per Order', readonly=True)
    total_orders = fields.Integer('Total Orders', readonly=True)
    total_delivered_orders = fields.Integer('Total Delivered Orders', readonly=True)
    total_rejected_orders = fields.Integer('Total Rejected Orders', readonly=True)
    average_delivery_time = fields.Float('Average Delivery Time (Days)', readonly=True)
    median_delivery_time = fields.Float('Median Delivery Time (Days)', readonly=True)
    no_availability = fields.Integer('Orders with No Availability', readonly=True)

    def print_provider_report(self):
        return self.env.ref('pms.provider_report_pdf_action').report_action(self)

    @property
    def _table_query(self):
        return f"""
            SELECT
                provider.id AS id,
                provider.name AS provider_name,
                (COUNT(CASE WHEN mat.order_status = 'rejected' THEN 1 END)::float / COUNT(*)) * 100 AS pct_rejection,
                AVG(mat.rejections_count)::float AS average_rejection_per_order,
                COUNT(*) AS total_orders,
                COUNT(CASE WHEN mat.order_status = 'delivered' THEN 1 END) AS total_delivered_orders,
                COUNT(CASE WHEN mat.order_status = 'rejected' THEN 1 END) AS total_rejected_orders,
                AVG(CASE WHEN mat.order_status = 'delivered' THEN mat.time_to_delivered END)::float AS average_delivery_time,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CASE WHEN mat.order_status = 'delivered' THEN mat.time_to_delivered END) AS median_delivery_time,
                COUNT(CASE WHEN mat.provider_no_availability = provider.id THEN 1 END) AS no_availability
            FROM
                pms_materials mat
            JOIN
                res_partner provider ON mat.provider = provider.id
            GROUP BY
                provider.id, provider.name
            ORDER BY
                provider.name
        """




