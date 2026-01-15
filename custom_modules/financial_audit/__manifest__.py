# -*- coding: utf-8 -*-

{
    'name': 'Financial Audit',
    'version': '1.2',
    'category': 'Services/financial_audit',
    'depends': ['base', 'account_payment', 'account', 'documents', 'analytic', 'purchase', 'stock', 'sale', 'hr_expense'],
    'description': "Module to audit financial data",
    'installable': True,
    'application': True,
    'data': [
        'security/group.xml',
        'security/ir.model.access.csv',
        'views/audit_test.xml',
        'views/audit_result.xml',
        'views/audit_menu.xml',
    ],
}
