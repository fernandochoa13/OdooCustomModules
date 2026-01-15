# -*- coding: utf-8 -*-

{
    'name': 'Whatsapp Connector',
    'version': '18.0.1.0.15',
    'category': 'Base',
    'depends': ['base', 'mail', 'account', 'account_followup'],
    'description': "Module to connect to whatsapp",
    'installable': True,
    'application': True,
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_connector.xml',
        'views/res_partner.xml',
        'views/account_followup_line.xml',
        'views/account_move.xml',
        'wizard/send_ws_message.xml',
        'wizard/send_invoice.xml',
    ],
}
