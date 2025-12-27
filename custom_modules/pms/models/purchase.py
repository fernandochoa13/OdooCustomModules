from odoo import api, models, fields
from odoo.tools import SQL
from odoo.exceptions import ValidationError
from datetime import datetime, time, timedelta
from odoo.fields import Command
from datetime import date
import base64
import io

class PurchaseOrder(models.Model):
    _inherit = ["purchase.order"]

    order_type = fields.Selection(selection=[("materials","Materials"), ("jobs", "Jobs")])

    analytic_accounts = fields.Char(string="Analytic Account", compute="_getlinesanalytic", store=True)

    @api.depends("order_line.analytic_distribution")
    def _getlinesanalytic(self):
        for record in self:
            analytic_ids = record.env["purchase.order.line"].sudo().search([("order_id", "=", record.id)])
            if analytic_ids:
                address_final = []
                for analytic_id in analytic_ids:
                    analytic_i = analytic_id.analytic_distribution
                    if analytic_i:
                        for key in analytic_i.keys():
                            address = record.env["account.analytic.account"].sudo().search([("id", "=", key)]).name
                            address_final.append(address)
                
                address_final = ",".join(str(element) for element in address_final)
                record.analytic_accounts = address_final
            else:
                record.analytic_accounts = ""
    
                 
class PurchaseOrderLine(models.Model):
    _inherit = ["purchase.order.line"]

    project_activity = fields.Many2one("pms.projects.routes")