# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class Investments(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'c30_investments'
    _description = "Investments"

    active = fields.Boolean(default=True)
    sequence = fields.Integer('Sequence', default=1)
    name = fields.Char(string='Description', index=True, required=True, translate=True, tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
        tracking=True,
        default=lambda self: self.env.company.id
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id,
        tracking=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        tracking=True,
        help="The customer that is investing",
        domain="['|', ('company_id', '=', company_id), ('company_id', '=', False)]"
    )
    contacted_by_id = fields.Many2one(
        'res.users',
        string='Contacted By',
        help="The user who made contact",
        domain="[('share', '=', False)]",
        tracking=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Client From',
        tracking=True,
        help="Responsible who made the contact for the investment",
        domain="[('share', '=', False)]"
    )
    last_contact = fields.Datetime(
        string='Last Contact',
        tracking=True,
        help="The date and time of the last contact with the investor."
    )
    lang = fields.Many2one(
        'res.lang', string='Language', help="The preferred language of the client.", tracking=True)
    value = fields.Monetary(
        string='Investment amount',
        help="Investment amount as a floating-point number",
        tracking=True
    )
    investor_self_usage = fields.Selection(
        [
            ('investor', 'Investor'),
            ('self_usage', 'Self Usage'),
        ],
        string='Investor/Self Usage',
        help="Whether the investment is made by an investor or for self-usage",
        tracking=True
    )
    type = fields.Selection(
        [
            ('lt_rent', 'LT Rent'),
            ('st_rent', 'ST Rent'),
            ('flipping', 'Flipping'),
            ('flip_villa', 'Fix&Flip Villa'),
            ('flip_apt', 'Fix&Flip Apt'),
        ],
        string='Type of investment',
        help="Specify the type of investment",
        tracking=True
    )
    desired_return = fields.Float(
        string='Desired Return',
        help="The desired return on investment as a floating-point number.",
        tracking=True
    )
    ready_off_plan = fields.Selection(
        [
            ('ready', 'Ready'),
            ('off', 'Off-plan'),
            ('both', 'Both'),
        ],
        string='Ready/Off-plan',
        help="Whether the investment is for a ready property, an off-plan property or both",
        tracking=True
    )
    interests = fields.Text(
        string='Interests', help="Interests or preferences of the investor as a text field.", tracking=True)
    properties_count = fields.Integer('Properties count', compute='_compute_properties_count')

    @api.depends('partner_id', 'company_id')
    def _compute_properties_count(self):
        if self.ids:
            counts_data = self.env["plus.properties"].read_group([
                ('partner_id', 'in', self.mapped("partner_id").ids),
                '|',
                ('company_id', 'in', self.mapped("company_id").ids),
                ('company_id', '=', False)
            ], ['partner_id'], ['partner_id'])
            mapped_data = {
                count['partner_id'][0]: count['partner_id_count'] for count in counts_data
            }
        else:
            mapped_data = {}

        for investment in self:
            investment.properties_count = mapped_data.get(investment.partner_id.id, 0)

    def action_see_properties(self):
        self.ensure_one()
        return {
            'name': _('Properties'),
            'domain': [
                ('partner_id', '=', self.partner_id.id),
                '|',
                ('company_id', '=', self.company_id.id),
                ('company_id', '=', False)
            ],
            'res_model': 'plus.properties',
            'type': 'ir.actions.act_window',
            'views': [
                (False, 'tree'),
                (False, 'form'),
                (False, 'kanban'),
                (False, 'calendar'),
                (False, 'map'),
                (False, 'pivot'),
                (False, 'graph')
            ],
            'view_mode': 'tree',
            'context': {
                "default_partner_id": self.partner_id.id,
                "default_company_id": self.company_id.id,
            },
        }
