from odoo import models, fields


class accounting_rules(models.Model):
    _name = 'accounting.rules'
    _description = 'Accounting Rules'

    vendor = fields.Many2one('res.partner', string='Vendor')
    sequence = fields.Integer(string='Sequence', required=True)
    county = fields.Many2one('pms.county', string='County of Applicability')
    payment_method = fields.Selection([('check', 'Check'), ('credit_card', 'Credit Card'), ('direct_deposit', 'Direct Deposit'), ('check_or_cc', 'Check or Credit Card')], string='Payment Method', default='check', required=True)
    company = fields.Many2one('res.company', string='Company', required=True)
    responsible_to_pay = fields.Many2one('res.users', string='Responsible to Pay')
    material_labor = fields.Selection([('material', 'Material'), ('labor', 'Labor')], string='Material or Labor')
    billable = fields.Boolean(string='Billable')
    markup = fields.Float(string='Markup')
    pre_invoiced = fields.Boolean(string='Pre-Invoiced')
    pre_invoiced_product = fields.Many2one('product.template', string='Pre-Invoiced Product')
    account_to_auto_complete = fields.Many2one('account.account', string='Account to Auto Complete')
    notes_for_user = fields.Text(string='Notes for User')
    applies_to = fields.Selection([('all', 'All'), ('own', 'Own'), ('third', 'Third'), ('escrow', 'Escrow'), ('on_hold', 'On Hold')], string='Applies To', default='all', required=True)
    if_own_go_to_owner = fields.Boolean(string='If Own Go to Owner', default=True)
    if_escrow_go_to_owner = fields.Boolean(string='If Own Go to Escrow Company', default=True)
    house_status = fields.Selection([('construction', 'Construction'), ('rented', 'Rented')])

    classify_folder = fields.Boolean(string='Classify Folder')
    folder = fields.Many2one('documents.folder', string='Folder')

    allowed_products = fields.Many2many('product.template', string='Allowed Products')



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    accounting_rules = fields.Many2many('accounting.rules', string='Accounting Rules')
