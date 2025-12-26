# -*- coding: utf-8 -*-

import datetime
from odoo import models, fields, api, _
# from odoo.addons.website.models.ir_http import slug
from odoo.osv import expression
from ..tools.constants import DEFAULT_WEBSITE_KEYS_FACTS, STATE_ATTRIBUTE_ID, CITY_ATTRIBUTE_ID


class PlusProperties(models.Model):
    _inherit = [
        'mail.thread',
        'mail.activity.mixin',
        'website.published.multi.mixin',
        'website.searchable.mixin',
        'image.mixin',
        'documents.mixin'
    ]
    _name = 'plus.properties'
    _description = "Properties"

    def _default_content(self):
        return DEFAULT_WEBSITE_KEYS_FACTS

    active = fields.Boolean(default=True)
    name = fields.Char(string='Title', index=True, required=True, translate=True)
    country_id = fields.Many2one(
        'res.country', string='Country', ondelete='restrict', default=lambda self: self.env.ref('base.us'))
    state_id = fields.Many2one(
        "res.country.state",
        string='State',
        ondelete='restrict',
        domain="[('country_id', '=?', country_id)]",
        default=lambda self: self.env.ref('base.state_us_10')
    )
    city_id = fields.Many2one(comodel_name='res.city', string='City', domain="[('state_id', '=?', state_id)]")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        index=True,
        default=lambda self: self.env.company.id
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
        domain="[('share', '=', False)]"
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Contact",
    )
    partner_email = fields.Char(
        related="partner_id.email",
        store=True,
        string="Email",
    )
    partner_phone = fields.Char(
        related="partner_id.phone",
        store=True,
        string="Phone",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency"
    )
    address = fields.Char(string='Address', compute='_compute_address')
    about_text = fields.Text(string='About text')
    color = fields.Integer(string='Color')
    area = fields.Integer(string='Area')
    bathrooms = fields.Integer(string='Bathrooms')
    bedrooms = fields.Integer(string='Bedrooms')
    commission = fields.Char(string='Commission')
    date = fields.Date(string='Date')
    rented_till = fields.Date(string='Rented Till')
    garage = fields.Integer(string='Garage')
    value = fields.Float(string='Price')
    kanban_state = fields.Selection(
        string="Kanban State",
        selection=[
            ("normal", "In Progress"),
            ("done", "Ready"),
            ("blocked", "Blocked")
        ]
    )
    property_type = fields.Selection(
        string="Property Type",
        selection=[
            ("residential", "Residential"),
            ("commercial", "Commercial"),
            ("industrial", "Industrial"),
            ("raw", "Raw land")
        ]
    )
    unit_type = fields.Selection(
        string="Unit type",
        selection=[
            ("apartment", "Apartment"),
            ("villa", "Villa"),
            ("office", "Office")
        ]
    )
    rent_type = fields.Selection(
        string="Rent Type",
        selection=[
            ("monthly", "Monthly"),
            ("annually", "Annually"),
        ],
        default="monthly"
    )
    website_key_facts = fields.Html(string="Key facts", default=_default_content, sanitize=False)
    sequence = fields.Integer('Sequence', default=1)
    service_charges = fields.Float(string="Service charges")
    website_description = fields.Html(string="Website HTML Description")
    is_vacant = fields.Boolean(string="Is Vacant?", store=True, compute="_compute_is_vacant")
    document_count = fields.Integer('Document Count', compute='_compute_document_count')
    images_attachment_ids = fields.One2many(
        comodel_name='ir.attachment', inverse_name='plus_property_images_id', string="Pictures")
    views_attachment_ids = fields.One2many(
        comodel_name='ir.attachment', inverse_name='plus_property_views_id', string="Views")
    marketing_attachment_ids = fields.One2many(
        comodel_name='ir.attachment', inverse_name='plus_property_marketing_id', string="Marketing material (PDFs)")
    legal_attachment_ids = fields.One2many(
        comodel_name='ir.attachment', inverse_name='plus_property_legal_id', string="Title and others (PDFs)")
    website_size_x = fields.Integer('Size X', default=1)
    website_size_y = fields.Integer('Size Y', default=1)
    website_ribbon_id = fields.Many2one('product.ribbon', string='Ribbon')

    def _get_attachment_domains(self):
        self.ensure_one()
        return [[('res_model', '=', 'plus.properties'), ('res_id', '=', self.id)]]

    def _compute_attachment(self):
        for record in self:
            record.property_attachment_ids = self.env['ir.attachment'].search(
                expression.OR(record._get_attachment_domains()))

    def _compute_website_url(self):
        super(PlusProperties, self)._compute_website_url()
        for property in self:
            if property.id:
                property.website_url = "/properties/property/%s" % self.env['ir.http']._slug(property)

    @api.depends("rented_till", "value")
    def _compute_is_vacant(self):
        for record in self:
            record.is_vacant = not record.rented_till or record.rented_till < datetime.date.today()

    @api.depends("country_id", "state_id", "city_id")
    def _compute_address(self):
        for record in self:
            address = []
            if record.city_id:
                address.append(record.city_id.name)
            if record.state_id:
                address.append(record.state_id.code)
            record.address = ", ".join(address)

    def _get_document_vals(self, attachment):
        document_vals = super(PlusProperties, self)._get_document_vals(attachment)
        document_vals["plus_property_id"] = self.id
        if attachment.plus_property_images_id:
            folder = self.env.ref('ao_properties.documents_properties_pictures_folder', raise_if_not_found=False)
            document_vals['folder_id'] = folder and folder.id
        if attachment.plus_property_views_id:
            folder = self.env.ref('ao_properties.documents_properties_views_folder', raise_if_not_found=False)
            document_vals['folder_id'] = folder and folder.id
        if attachment.plus_property_marketing_id:
            folder = self.env.ref('ao_properties.documents_properties_marketing_folder', raise_if_not_found=False)
            document_vals['folder_id'] = folder and folder.id
        if attachment.plus_property_legal_id:
            folder = self.env.ref('ao_properties.documents_properties_legal_folder', raise_if_not_found=False)
            document_vals['folder_id'] = folder and folder.id
        return document_vals

    def _get_document_owner(self):
        return self.user_id or self.env.user

    def _get_document_folder(self):
        return self.env.ref('ao_properties.documents_properties_folder', raise_if_not_found=False)

    def _get_document_partner(self):
        return self.partner_id

    def _check_create_documents(self):
        return True

    def _get_property_document_domain(self):
        self.ensure_one()
        return [('plus_property_id', '=', self.id)]

    def _compute_document_count(self):
        for property in self:
            property.document_count = self.env['documents.document'].search_count(
                property._get_property_document_domain())

    def action_see_documents(self):
        self.ensure_one()
        properties_folder = self.env.ref('ao_properties.documents_properties_folder', raise_if_not_found=False)
        return {
            'name': _('Documents'),
            'domain': [('plus_property_id', '=', self.id)],
            'res_model': 'documents.document',
            'type': 'ir.actions.act_window',
            'views': [(False, 'kanban')],
            'view_mode': 'kanban',
            'context': {
                "default_partner_id": self.partner_id.id,
                "default_plus_property_id": self.id,
                "default_res_id": self.id,
                "default_company_id": self.company_id.id,
                "default_res_model": "plus.properties",
                "searchpanel_default_folder_id": properties_folder and properties_folder.id
            },
        }

    @api.model
    def _search_get_detail(self, website, order, options):
        with_image = options['displayImage']
        with_price = options['displayDetail']
        domains = [website.website_property_domain()]
        min_price = options.get('min_price')
        max_price = options.get('max_price')
        attrib_values = options.get('attrib_values')
        if min_price:
            domains.append([('value', '>=', min_price)])
        if max_price:
            domains.append([('value', '<=', max_price)])
        if attrib_values:
            state_ids = []
            city_ids = []
            for value in attrib_values:
                if value[0] == str(STATE_ATTRIBUTE_ID):
                    state_ids.append(int(value[1]))
                elif value[0] == str(CITY_ATTRIBUTE_ID):
                    city_ids.append(int(value[1]))
            if state_ids:
                domains.append([('state_id', 'in', state_ids)])
            if city_ids:
                domains.append([('city_id', 'in', city_ids)])
        search_fields = ['name']
        fetch_fields = ['id', 'name', 'website_url']
        mapping = {
            'name': {'name': 'name', 'type': 'text', 'match': True},
            'website_url': {'name': 'website_url', 'type': 'text', 'truncate': False},
        }
        if with_image:
            mapping['image_url'] = {'name': 'image_url', 'type': 'html'}
        if with_price:
            mapping['detail'] = {'name': 'value', 'type': 'html'}
        return {
            'model': 'plus.properties',
            'base_domain': domains,
            'search_fields': search_fields,
            'fetch_fields': fetch_fields,
            'mapping': mapping,
            'icon': 'fa-folder-o',
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        with_image = 'image_url' in mapping
        with_price = 'detail' in mapping
        results_data = super()._search_render_results(fetch_fields, mapping, icon, limit)
        for plus_property, data in zip(self, results_data):
            if with_price:
                data['price'] = plus_property.value
            if with_image:
                data['image_url'] = '/web/image/plus.properties/%s/image_128' % data['id']
        return results_data

    def _get_images(self):
        self.ensure_one()
        return [self] + list(self.images_attachment_ids)

    def _get_suitable_image_size(self, columns, x_size, y_size):
        if x_size == 1 and y_size == 1 and columns >= 3:
            return 'image_512'
        return 'image_1024'

    def _get_website_ribbon(self):
        return self.website_ribbon_id
