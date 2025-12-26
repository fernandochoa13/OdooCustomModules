# -*- coding: utf-8 -*-
{
    'name': "ao_sales",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "plusteam",
    'website': "https://www.plusteam.tech",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '18.0.0.0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'base_automation', 'crm', 'mass_mailing', 'auth_api_key'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/crm_lead_views.xml',
    ],
}
