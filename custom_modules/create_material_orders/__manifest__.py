# -*- coding: utf-8 -*-

{
    'name': 'Create Material Orders',
    'version': '18.0.1.0.0',
    'category': 'Services',
    'depends': ['base', 'account_payment', 'account', 'documents', 'analytic', 'purchase', 'stock', 'sale', 'hr_expense', 'pms'],
    'license': 'LGPL-3',
    'description': "Module to manage easily create material orders",
    'installable': True,
    'application': False,
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/create_order_wizard.xml',
        'views/successful_order.xml',
        'views/order_report.xml',
        'views/confirm_orders.xml',
        'views/send_order_message_view.xml',
        'views/create_order_menu.xml'
    ],
    'assets': {
            'web.assets_backend': [
                'create_material_orders/static/src/css/kanban.css',
                'create_material_orders/static/src/xml/kanban_back_button.xml',
                'create_material_orders/static/src/js/kanban_back_extend.js',
            ],
},
}
