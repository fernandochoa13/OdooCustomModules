# -*- coding: utf-8 -*-

from odoo import http, tools, _
from odoo.tools import lazy
from odoo.http import request
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website_sale.controllers.main import TableCompute
from ..tools.constants import STATE_ATTRIBUTE_ID, CITY_ATTRIBUTE_ID


class PlusProperties(http.Controller):

    @http.route(
        ['/properties/property/<model("plus.properties"):plus_property>'], type='http', auth="public", website=True, sitemap=True)
    def plus_property(self, plus_property, search='', **kwargs):
        return request.render("ao_properties.property_template", {
                'search': search,
                'plus_property': plus_property,
                'keep': QueryURL('/properties', search=search),
            }
        )

    def sitemap_properties(env, rule, qs):
        if not qs or qs.lower() in '/properties':
            yield {'loc': '/properties'}

    def _properties_get_query_url_kwargs(self, search, min_price, max_price, order=None, **post):
        return {
            'search': search,
            'min_price': min_price,
            'max_price': max_price,
            'order': order,
        }

    def _get_search_options(self, attrib_values=None, min_price=0.0, max_price=0.0, conversion_rate=1, **post):
        return {
            'displayDescription': True,
            'displayDetail': True,
            'displayImage': True,
            'attrib_values': attrib_values,
            'allowFuzzy': not post.get('noFuzzy'),
            'min_price': min_price / conversion_rate,
            'max_price': max_price / conversion_rate,
        }

    def _get_search_order(self, post):
        order = post.get('order') or request.env['website'].get_current_website().properties_default_sort
        return 'is_published desc, %s, id desc' % order

    def _lookup_properties(self, options, post, search, website):
        property_count, details, fuzzy_search_term = website._search_with_fuzzy(
            "plus_properties", search, limit=None, order=self._get_search_order(post), options=options)
        search_result = details[0].get('results', request.env['plus.properties']).with_context(bin_size=True)
        return fuzzy_search_term, property_count, search_result

    def get_id_value_attrib(self, attribute):
        return tuple([attribute.id, attribute.name])

    @http.route([
        '/properties',
        '/properties/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_properties)
    def properties(self, page=0, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        add_qty = int(post.get('add_qty', 1))
        try:
            min_price = float(min_price)
        except ValueError:
            min_price = 0
        try:
            max_price = float(max_price)
        except ValueError:
            max_price = 0
        website = request.env['website'].get_current_website()
        if ppg:
            try:
                ppg = int(ppg)
                post['ppg'] = ppg
            except ValueError:
                ppg = False
        if not ppg:
            ppg = website.properties_ppg or 15

        ppr = website.properties_ppr or 3
        keep = QueryURL('/properties', **self._properties_get_query_url_kwargs(search, min_price, max_price, **post))

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[x for x in v.split("-")] for v in attrib_list if v]
        attributes_ids = {v[0] for v in attrib_values}
        attrib_set = {v[1] for v in attrib_values}

        filter_by_price_enabled = website.is_view_active('website_sale.filter_products_price')
        #if filter_by_price_enabled:
        #    company_currency = website.company_id.currency_id
        #    conversion_rate = request.env['res.currency']._get_conversion_rate(
        #        company_currency, pricelist.currency_id, request.website.company_id, fields.Date.today())
        #else:
        #    conversion_rate = 1

        url = "/properties"
        if search:
            post["search"] = search

        options = self._get_search_options(
            attrib_values=attrib_values,
            min_price=min_price,
            max_price=max_price,
            **post
        )
        fuzzy_search_term, property_count, search_product = self._lookup_properties(
            options, post, search, website)

        pager = website.pager(url=url, total=property_count, page=page, step=ppg, scope=7, url_args=post)
        offset = pager['offset']
        properties = search_product[offset:offset + ppg]


        layout_mode = request.session.get('website_sale_shop_layout_mode')
        if not layout_mode:
            layout_mode = 'grid'
            request.session['website_sale_shop_layout_mode'] = layout_mode

        attributes = []
        if properties:
            initial_attributes = [
                {
                    "id": STATE_ATTRIBUTE_ID,
                    "name": _("State"),
                    "field": "state_id",
                    "display_type": "select",
                    "value_ids": list(map(self.get_id_value_attrib, properties.mapped('state_id')))
                },
                {
                    "id": CITY_ATTRIBUTE_ID,
                    "name": _("City"),
                    "field": "city_id",
                    "display_type": "select",
                    "value_ids": list(map(self.get_id_value_attrib, properties.mapped('city_id')))
                }
            ]
            attributes.extend(initial_attributes)

        values = {
            'search': fuzzy_search_term or search,
            'original_search': fuzzy_search_term and search,
            'order': post.get('order', ''),
            'pager': pager,
            'add_qty': add_qty,
            'attributes': attributes,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'properties': properties,
            'search_product': search_product,
            'search_count': property_count,
            'bins': lazy(lambda: TableCompute().process(properties, ppg, ppr)),
            'ppg': ppg,
            'ppr': ppr,
            'keep': keep,
            'layout_mode': layout_mode,
            'float_round': tools.float_round,
        }
        return request.render("ao_properties.properties_template", values)
