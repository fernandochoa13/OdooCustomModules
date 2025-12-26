# -*- coding: utf-8 -*-

from odoo import models, fields, _
from odoo.osv import expression


class Website(models.Model):
    _inherit = 'website'

    @staticmethod
    def _get_property_sort_mapping():
        return [
            ('sequence asc', _('Featured')),
            ('create_date desc', _('Newest Arrivals')),
            ('name asc', _('Name (A-Z)')),
            ('name desc', _('Name (Z-A)')),
            ('value asc', _('Price - Low to High')),
            ('value desc', _('Price - High to Low')),
        ]

    properties_default_sort = fields.Selection(
        selection='_get_property_sort_mapping', default='sequence asc', required=True)
    properties_ppg = fields.Integer(default=15, string="Number of properties in the grid on the properties page")
    properties_ppr = fields.Integer(default=3, string="Number of grid columns on the properties page")
    website_property_type = fields.Selection(
        selection=[
            ('rent', 'Rent'),
            ('sell', 'Sell'),
        ],
        default='sell'
    )

    def _search_get_details(self, search_type, order, options):
        result = super()._search_get_details(search_type, order, options)
        if search_type in ['plus_properties', 'all']:
            result.append(self.env['plus.properties']._search_get_detail(self, order, options))
        return result

    def website_property_domain(self):
        return expression.AND([self._property_domain(), self.get_current_website().website_domain()])

    def _property_domain(self):
        return [('active', '=', True)]
