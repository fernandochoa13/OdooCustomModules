from odoo import fields, models, api


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    amount_paid = fields.Monetary(string="Amount Paid", currency="currency_id", compute='_compute_amount_paid')
    amount_due = fields.Monetary(string="Amount Due", currency="currency_id", compute='_compute_amount_due')
    ao_payment_state = fields.Selection(string="Payment State", selection=[
        ('pending_payment', "Pending Payment"),
        ('fully_paid', 'Fully Paid')
    ], compute="_compute_ao_payment_state")

    @api.depends('invoice_ids', 'invoice_ids.amount_total', 'invoice_ids.amount_residual')
    def _compute_amount_paid(self):
        for sale_order in self:
            invoices = sale_order.invoice_ids.filtered(
                lambda invoice: invoice.state != 'draft' and invoice.move_type == "out_invoice"
            )
            if not invoices:
                sale_order.amount_paid = 0
                continue
            sale_order.amount_paid = sum(invoices.mapped('amount_total')) - sum(invoices.mapped('amount_residual'))

    @api.depends('amount_paid', 'amount_total')
    def _compute_amount_due(self):
        for sale_order in self:
            sale_order.amount_due = sale_order.amount_total - sale_order.amount_paid

    @api.depends('amount_due')
    def _compute_ao_payment_state(self):
        for sale_order in self:
            if sale_order.amount_due == 0:
                sale_order.ao_payment_state = 'fully_paid'
                continue
            sale_order.ao_payment_state = 'pending_payment'
