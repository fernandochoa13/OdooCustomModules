# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError, UserError
from odoo import fields
from freezegun import freeze_time
from unittest.mock import patch, call, MagicMock


class TestPMSMaterials(TransactionCase):
    def setUp(self):
        super(TestPMSMaterials, self).setUp()

        # Create some basic related records for testing
        self.employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        self.partner = self.env['res.partner'].create({'name': 'Partner A'})
        self.city = self.env['pms.cities'].search([("name", "=", "Orlando")])
        self.analytical_plan = self.env['account.analytic.plan'].search([('name', '=', 'Properties')])
        self.analytical_account = self.env['account.analytic.account'].create({
                'name': 'Test Analytic Account', 
                'plan_id': self.analytical_plan.id,
            })
        self.property = self.env['pms.property'].create({
            'address': '123 Main St',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': self.city.id,
            'parcel_id': "1",
            'zipcode': 32809,
            'nunits': 1,
            'analytical_account': self.analytical_account.id,
            'analytical_plan': self.analytical_plan.id,
            'partner_id': self.partner.id
        })
        self.project_routes_template = self.env['pms.projects.routes.templates'].create({'name': 'New Ocala Route'})
        self.template_line = self.env['pms.projects.routes.templates.lines'].create({
            'name': 'OC Engineering Fee',
            'route_header': self.project_routes_template.id,
            'sequence': 1,
            'phase': 'pip'
        })
        self.project = self.env['pms.projects'].create({
            'address': self.property.id,
            'project_routes': self.project_routes_template.id,
            'project_manager': self.employee.id,
            'superintendent': self.employee.id,
            'zone_coordinator': self.employee.id,
            'visit_day': 'monday',
            'second_visit_day': 'tuesday',
            'status_construction': 'coc'
        })
        self.payment_term = self.env['account.payment.term'].create({'name': 'Payment Term'})
        self.company = self.env['res.company'].create({'name': 'Test Company'})
        self.journal = self.env['account.journal'].create({'name': 'Test Journal Bank', 'type': 'bank', 'code': '111', 'company_id': self.company.id})
        self.journal = self.env['account.journal'].create({'name': 'Test Journal Sale', 'type': 'sale', 'code': '1111', 'company_id': self.company.id})
        self.outstanding_account = self.env['account.account'].create({
            'code': '101999',
            'name': 'Outstanding Payments',
            'company_id': self.company.id,
            'account_type': 'asset_current'
        })
        # self.account = self.env['account.account'].create({'name': 'Test Account', 'code': 'TA', 'user_type_id': self.env.ref('account.data_account_type_payable').id})
        self.purchase_template = self.env['purchase.template'].create({'name': 'Test Template'})
        self.account = self.env['account.account'].search([('code', '=', '4000001')], limit=1)
        self.house_model = self.env['pms.housemodels'].create({'name': 'Test House Model'})
        self.product = self.env['product.product'].create({'name': 'Test Product', 'property_account_income_id': self.account.id})
        self.property_owner = self.env['res.partner'].create({'name': 'Test Owner'})
        self.provider = self.env['res.partner'].create({'name': 'Test Provider'})
        self.subproduct = self.env['product.subproduct'].create({'name': 'Test Sub-Product'})
        self.payment_term_line = self.env['account.payment.term.line'].create({
            'days': 30,
            'payment_id': self.payment_term.id,
        })
        self.html_content = "<p>This is a test email.</p>"

    # def test_create_invoice_without_payment_term(self):
    #     material_order_no_term = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'property_owner': self.property_owner.id,
    #         'provider': self.provider.id,
    #         'company_third_party': self.company.id,
    #         'name': 'MO009',
    #     })
    #     with self.assertRaises(UserError) as cm:
    #         material_order_no_term.create_invoice()

    # def test_create_invoice_without_payment_term_lines(self):
    #     payment_term_no_lines = self.env['account.payment.term'].create({'name': 'Test Payment Term No Lines'})
    #     material_order_no_term_lines = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'property_owner': self.property_owner.id,
    #         'provider': self.provider.id,
    #         'company_third_party': self.company.id,
    #         'payment_terms': payment_term_no_lines.id,
    #         'name': 'MO010',
    #     })
    #     with self.assertRaises(UserError) as cm:
    #         material_order_no_term_lines.create_invoice()

"""    def test_create_invoice_success(self):

        material_payment_term = self.env['account.payment.term'].create({
            'name': 'Material Payment Term',
            'line_ids': [
                (0, 0, {'value': 'percent', 'value_amount': 100.0, 'days': 0}),
                (0, 0, {'value': 'balance', 'value_amount': 0, 'days': 0}),
            ],
            'material_payment': True,
        })

        regular_payment_term = self.env['account.payment.term'].create({
            'name': 'Regular Payment Term',
            'line_ids': [
                (0, 0, {'value': 'percent', 'value_amount': 50.0, 'days': 15}),
                (0, 0, {'value': 'balance', 'value_amount': 50.0, 'days': 30}),
            ],
        })
        
        self.product.property_account_income_id = self.outstanding_account.id
        
        material_order = self.env['pms.materials'].create({
            'property_id': self.property.id,
            'property_owner': self.property_owner.id,
            'provider': self.provider.id,
            'company_third_party': self.company.id,
            'payment_terms': regular_payment_term.id,
            'name': 'test',
        })
        material_line = self.env['pms.materials.lines'].create({
            'material_order_id': material_order.id,
            'product': self.product.id,
            'subproduct': self.subproduct.id,
            'quantity': 2,
            'amount': 100.0,
        })
        action = material_order.create_invoice()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['name'], 'Customer Invoice')
        self.assertEqual(action['res_model'], 'account.move')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['view_type'], 'form')
        self.assertEqual(action['target'], 'current')
        self.assertTrue(material_order.linked_invoice)
        self.assertEqual(action['res_id'], material_order.linked_invoice)

        invoice = self.env['account.move'].browse(material_order.linked_invoice)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.partner_id, self.property_owner)
        self.assertEqual(invoice.company_id, self.company_third_party)
        self.assertEqual(invoice.contractor, self.provider)
        self.assertEqual(invoice.linked_material_order, material_order)
        self.assertEqual(invoice.payment_reference, material_order.name)
        self.assertEqual(invoice.invoice_line_ids[0].name, self.subproduct.name)
        self.assertEqual(invoice.invoice_line_ids[0].product_id, self.product)
        self.assertEqual(invoice.invoice_line_ids[0].quantity, material_line.quantity)
        self.assertEqual(invoice.invoice_line_ids[0].price_unit, material_line.amount)
        self.assertIn(self.property.analytical_account.id, invoice.invoice_line_ids[0].analytic_distribution)

        expected_due_date = fields.Date.today()
        self.assertEqual(invoice.invoice_date_due, expected_due_date)
        self.assertEqual(invoice.state, 'draft')

        self.assertEqual(invoice.invoice_payment_term_id, material_payment_term)"""
        
        
    # @patch('odoo.addons.mail.models.mail_mail.MailMail.send')
    # def test_notify_when_special_order_approved_true(self, mock_mail_send):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Special Order Test',
    #         'special_order': True,
    #         'special_order_approved': False,
    #     })
    #     material_order.special_order_approved = True
    #     material_order.notify_when_special_order_approved()

    #     expected_email_to = "adan@adanordonezp.com"
    #     expected_subject = f'Special Order Approved: {material_order.name}'
    #     expected_body_content = f"<p><span style=\"font-weight: bold; color: #28a745;\">{material_order.name}</span></p>"

    #     mock_mail_send.assert_called_once()
    #     args, _ = mock_mail_send.call_args
    #     mail_values = args[0]
    #     self.assertEqual(mail_values['subject'], expected_subject)
    #     self.assertEqual(mail_values['email_to'], expected_email_to)
    #     self.assertIn(expected_body_content, mail_values['body_html'])

    # @patch('odoo.addons.mail.models.mail_mail.MailMail.send')
    # def test_notify_when_special_order_approved_false(self, mock_mail_send):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Special Order Test',
    #         'special_order': True,
    #         'special_order_approved': False,
    #     })
    #     material_order.notify_when_special_order_approved()
    #     mock_mail_send.assert_not_called()

    # @patch('odoo.addons.mail.models.mail_mail.MailMail.send')
    # def test_notify_when_special_order_approved_already_true(self, mock_mail_send):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Special Order Test',
    #         'special_order': True,
    #         'special_order_approved': True,
    #     })
    #     material_order.write({'special_order_approved': True})
    #     mock_mail_send.assert_not_called()
        
        
        
    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_gave_pay')
    # def test_write_status_change_rejected(self, mock_send_email):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_status': 'waiting_payment',
    #         'name': 'MO004',
    #     })
    #     material_order.write({'order_status': 'rejected'})
    #     self.assertEqual(material_order.order_status, 'rejected')
    #     mock_send_email.assert_called_once()

    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_gave_pay')
    # def test_write_status_change_delivered(self, mock_send_email):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_status': 'waiting_payment',
    #         'name': 'MO004',
    #     })
    #     material_order.write({'order_status': 'delivered'})
    #     self.assertEqual(material_order.order_status, 'delivered')
    #     mock_send_email.assert_called_once()

    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_gave_pay')
    # def test_write_status_change_other(self, mock_send_email):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_status': 'waiting_payment',
    #         'name': 'MO004',
    #     })
    #     material_order.write({'payment_date': datetime.now()})
    #     self.assertEqual(material_order.payment_date.date(), datetime.now().date())
    #     mock_send_email.assert_not_called()

    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_gave_pay')
    # def test_write_no_status_change(self, mock_send_email):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_status': 'waiting_payment',
    #         'name': 'MO004',
    #     })
    #     material_order.write({'reference': 'NEW-REF'})
    #     self.assertEqual(material_order.reference, 'NEW-REF')
    #     mock_send_email.assert_not_called()

    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_gave_pay')
    # def test_write_initial_status_rejected(self, mock_send_email):
    #     not_tracked_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_status': 'not_ordered',
    #         'name': 'MO005',
    #     })
    #     not_tracked_order.write({'order_status': 'rejected'})
    #     self.assertEqual(not_tracked_order.order_status, 'rejected')
    #     mock_send_email.assert_called_once()

    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_gave_pay')
    # def test_write_initial_status_delivered(self, mock_send_email):
    #     not_tracked_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_status': 'not_ordered',
    #         'name': 'MO005',
    #     })
    #     not_tracked_order.write({'order_status': 'delivered'})
    #     self.assertEqual(not_tracked_order.order_status, 'delivered')
    #     mock_send_email.assert_called_once()

    # def test_create_pms_materials(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'payment_terms': self.payment_term.id,
    #         'payment_method': 'Bank Transfer',
    #         'payment_method_journal': self.journal.id,
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     self.assertTrue(material_order.id, "Material order should be created.")
    #     self.assertEqual(material_order.property_id, self.property, "Property should be linked correctly.")
    #     self.assertEqual(material_order.reference, 'TEST-REF-001', "Reference should be set correctly.")
    #     self.assertEqual(material_order.payment_terms, self.payment_term, "Payment terms should be linked.")

    # def test_compute_name(self):
    #     # Test case 1: With all fields
    #     estimated_delivery_date = fields.Datetime.today()
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'estimated_delivery_date': estimated_delivery_date,
    #         'reference': 'REF-123',
    #     })
    #     self.assertEqual(material_order.name, f"{self.property.name} | {estimated_delivery_date} | REF-123", "Name should include all parts.")

    #     # Test case 2: With only property_id
    #     material_order_prop = self.env['pms.materials'].create({'property_id': self.property.id})
    #     self.assertEqual(material_order_prop.name, f"{self.property.name}", "Name should include only property name.")

    #     # Test case 3: With property and reference
    #     material_order_prop_ref = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'REF-456',
    #     })
    #     self.assertEqual(material_order_prop_ref.name, f"{self.property.name} | REF-456", "Name should include property and reference.")

    #     # Test case 4: With no fields set
    #     material_order_empty = self.env['pms.materials'].create({})
    #     self.assertEqual(material_order_empty.name, "", "Name should be empty.")

    # def test_calc_order_creation(self):
    #     material_order = self.env['pms.materials'].create({'property_id': self.property.id})
    #     creation_date = material_order.order_creation_date.date() if material_order.order_creation_date else material_order.create_date.date()
    #     self.assertEqual(creation_date, date.today(), "Order creation date should match create date.")

    #     # Test when order_creation_date is already set
    #     specific_date = datetime.now() - timedelta(days=2)
    #     material_order.order_creation_date = specific_date
    #     material_order.calc_order_creation()
    #     self.assertEqual(material_order.order_creation_date.date(), specific_date.date(), "Order creation date should not change if already set.")

    # def test_calc_created_to_waiting_cust_days(self):
    #     order_creation_date = datetime.now() - timedelta(days=10)
    #     order_request_date = datetime.now() - timedelta(days=3)
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_creation_date': order_creation_date,
    #         'order_request_date': order_request_date,
    #     })
    #     self.assertEqual(material_order.created_to_waiting_cust, 7, "Should calculate the correct difference in days.")

    #     # Test with missing dates
    #     material_order_no_dates = self.env['pms.materials'].create({'property_id': self.property.id})
    #     self.assertEqual(material_order_no_dates.created_to_waiting_cust, 0, "Should be 0 if dates are missing.")

    # def test_calc_wait_to_gave_pay_days(self):
    #     order_request_date = datetime.now() - timedelta(days=7)
    #     ordered_date = datetime.now() - timedelta(days=1)
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'order_request_date': order_request_date,
    #         'ordered_date': ordered_date,
    #     })
    #     self.assertEqual(material_order.wait_to_gave_pay, 6, "Should calculate the correct difference in days.")
    
    #     # Test with missing dates
    #     material_order_no_dates = self.env['pms.materials'].create({'property_id': self.property.id})
    #     self.assertEqual(material_order_no_dates.wait_to_gave_pay, 0, "Should be 0 if dates are missing.")

    # def test_delivered_to_ordered_calculator(self):
    #     ordered_date = datetime.now().date() - timedelta(days=5)
    #     actual_delivery_date = datetime.now().date()
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'ordered_date': ordered_date,
    #         'actual_delivery_date': actual_delivery_date,
    #     })
    #     self.assertEqual(material_order.ordered_to_delivered, 5, "Should calculate the correct difference in days.")
    
    #     # Test with missing dates
    #     material_order_no_dates = self.env['pms.materials'].create({'property_id': self.property.id})
    #     self.assertEqual(material_order_no_dates.ordered_to_delivered, 0, "Should be 0 if dates are missing.")
    
    # def test_compute_last_followup(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({'property_id': self.property.id})

    #     # Create some followups
    #     followup1 = self.env['material.order.follow.up'].create({
    #         'material_id': material_order.id,
    #         'date': datetime.now() - timedelta(days=2),
    #         'comment': 'Followup 1 comment',
    #     })
    #     followup2 = self.env['material.order.follow.up'].create({
    #         'material_id': material_order.id,
    #         'date': datetime.now(),
    #         'comment': 'Latest followup comment',
    #     })
    #     followup3 = self.env['material.order.follow.up'].create({
    #         'material_id': material_order.id,
    #         'date': datetime.now() - timedelta(days=5),
    #         'comment': 'Followup 3 comment',
    #     })

    #     # Trigger the computation
    #     material_order._compute_last_followup()

    #     # Assert the computed values are correct
    #     self.assertEqual(material_order.last_followup_message, 'Latest followup comment', "Should be the latest comment")
    #     self.assertEqual(material_order.last_followup_date, followup2.date, "Should be the latest date")

    #     # Test when there are no followups
    #     material_order_no_followups = self.env['pms.materials'].create({'property_id': self.property.id})
    #     material_order_no_followups._compute_last_followup()
    #     self.assertFalse(material_order_no_followups.last_followup_message, "Should be False when no followups")
    #     self.assertFalse(material_order_no_followups.last_followup_date, "Should be False when no followups")


    # def test_set_delivered(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #     })

    #     # Call set_delivered
    #     material_order.set_delivered()

    #     # Assert that the order_status and actual_delivery_date are updated correctly
    #     self.assertEqual(material_order.order_status, 'delivered', "Order status should be set to 'delivered'")
    #     self.assertTrue(material_order.actual_delivery_date, "actual_delivery_date should be set")

    #     # Test that a ValidationError is raised for a special order that is not approved
    #     material_order.special_order = True
    #     with self.assertRaises(ValidationError):
    #         material_order.set_delivered()

    #     # Approve the order and try again
    #     material_order.special_order_approved = True
    #     material_order.set_delivered()
    #     self.assertEqual(material_order.order_status, 'delivered')
    #     self.assertTrue(material_order.actual_delivery_date)


    # def test_set_delivered_on_bulk(self):
    #     # Create some material orders with different statuses
    #     order1 = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Order 1',
    #         'order_status': 'ordered',
    #     })
    #     order2 = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Order 2',
    #         'order_status': 'delivered',
    #     })
    #     order3 = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Order 3',
    #         'order_status': 'not_ordered',
    #     })
    #     orders = order1 + order2 + order3

    #     # Call set_delivered_on_bulk
    #     orders.set_delivered_on_bulk()

    #     # Assert that the orders with the correct initial status are updated correctly
    #     self.assertEqual(order1.order_status, 'delivered', "Order 1 should be set to 'delivered'")
    #     self.assertTrue(order1.actual_delivery_date, "Order 1 should have actual_delivery_date set")
    #     self.assertEqual(order2.order_status, 'delivered', "Order 2 should remain 'delivered'")
    #     self.assertFalse(order3.actual_delivery_date, "Order 3 should not have actual_delivery_date set")
    #     self.assertEqual(order3.order_status, 'not_ordered', "Order 3 should not be modified")

        # Check for the notes posted.
        # messages = self.env['mail.message'].search([('res_id', 'in', orders.ids), ('model', '=', 'pms.materials')])
        # self.assertEqual(len(messages), 2, "Only 2 notes should be posted")
        # self.assertTrue("The following Material Order has been set to 'Delivered'" in messages[0].body)
        # self.assertTrue("Order Order 3 was not in 'Ordered' state." in messages[1].body)
        

    # def test_open_order(self):
    #     # Create a material order.
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #     })

    #     # Call open_order.
    #     action = material_order.open_order()

    #     # Assert that the returned action is correct.
    #     self.assertEqual(action['type'], 'ir.actions.act_window', "Should return an action of type ir.actions.act_window")
    #     self.assertEqual(action['res_id'], material_order.id, "Should open the correct material order")
    #     self.assertEqual(action['view_mode'], 'form', "Should open the form view")
    #     self.assertEqual(action['res_model'], 'pms.materials', "Should open the pms.materials model")

    # def test_redo_order(self):
    #     # Create a material order.
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #         'reference': 'REF-001',
    #         'order_creator': self.employee.id,
    #         'property_status': 'construction',
    #         'county': self.city,
    #         'property_owner': self.partner.id,
    #         'project_manager': self.employee.id,
    #         'zone_coordinator': self.employee.id,
    #         'superintendent': self.employee.id,
    #         'house_model': self.house_model.id,
    #         'on_hold': True,
    #         'own_third': True,
    #         'project_phase': 'pip',
    #         'provider': self.partner.id,
    #         'payment_terms_anticipated': 'anticipated',
    #         'payment_method': 'cash',
    #         'payment_method_journal': self.journal.id,
    #     })

    #     # Call redo_order.
    #     action = material_order.redo_order()

    #     # Assert that a new order is created.
    #     new_order = self.env['pms.materials'].search([('id', '=', action['res_id'])])
    #     self.assertTrue(new_order, "Should create a new material order")

    #     # Assert that the new order has the correct values.
    #     self.assertEqual(new_order.reference, 'Re-order: REF-001', "Should have the correct reference")
    #     self.assertEqual(new_order.property_id, material_order.property_id, "Should have the same property")
    #     self.assertEqual(new_order.order_creator, material_order.order_creator, "Should have the same order creator")
    #     self.assertEqual(new_order.property_status, material_order.property_status, "Should have the same property status")
    #     self.assertEqual(new_order.county, material_order.county, "Should have the same county")
    #     self.assertEqual(new_order.property_owner, material_order.property_owner, "Should have the same property owner")
    #     self.assertEqual(new_order.project_manager, material_order.project_manager, "Should have the same project manager")
    #     self.assertEqual(new_order.zone_coordinator, material_order.zone_coordinator, "Should have the same zone coordinator")
    #     self.assertEqual(new_order.superintendent, material_order.superintendent, "Should have the same superintendent")
    #     self.assertEqual(new_order.house_model, material_order.house_model, "Should have the same house model")
    #     self.assertEqual(new_order.on_hold, material_order.on_hold, "Should have the same on_hold value")
    #     self.assertEqual(new_order.own_third, material_order.own_third, "Should have the same own_third value")
    #     self.assertEqual(new_order.project_phase, material_order.project_phase, "Should have the same project phase")
    #     self.assertEqual(new_order.provider, material_order.provider, "Should have the same provider")
    #     self.assertEqual(new_order.payment_terms_anticipated, material_order.payment_terms_anticipated, "Should have the same payment terms anticipated")
    #     self.assertEqual(new_order.payment_method, material_order.payment_method, "Should have the same payment method")
    #     self.assertEqual(new_order.payment_method_journal, material_order.payment_method_journal, "Should have the same payment method journal")
    #     self.assertTrue(new_order.special_order, "Should be a special order")
    #     self.assertFalse(new_order.special_order_approved, "Should not be approved")

    #     # Assert that the original order is linked to the new order.
    #     self.assertTrue(material_order.re_order_id, "Original order should be linked to the new order")
    #     self.assertEqual(material_order.re_order_id[0].id, new_order.id, "Should be linked to the correct new order")

    #     # Assert that a note is posted on the new order.
    #     messages = self.env['mail.message'].search([('res_id', '=', new_order.id), ('model', '=', 'pms.materials')])
    #     self.assertTrue(messages, "Should have a note posted")
    #     self.assertTrue("Re-Order from Order:" in messages[0].body, "Should have the correct note content")

    #     # Assert that the returned action is correct.
    #     self.assertEqual(action['type'], 'ir.actions.act_window', "Should return an action of type ir.actions.act_window")
    #     self.assertEqual(action['res_id'], new_order.id, "Should open the new material order")
    #     self.assertEqual(action['view_mode'], 'form', "Should open the form view")
    #     self.assertEqual(action['res_model'], 'pms.materials', "Should open the pms.materials model")

    # def test_view_payment_request(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #     })
    #     # Test when there is no linked payment request
    #     with self.assertRaises(UserError):
    #         material_order.view_payment_request()

    #     # Create a payment request and link it to the material order
    #     payment_request = self.env['cc.programmed.payment'].create({'name': 'Test Payment Request'})
    #     material_order.linked_payment_request = payment_request.id

    #     # Call the view_payment_request method
    #     action = material_order.view_payment_request()

    #     # Assert that the action is correct
    #     self.assertEqual(action['type'], 'ir.actions.act_window', "Should return an action of type ir.actions.act_window")
    #     self.assertEqual(action['res_model'], 'cc.programmed.payment', "Should open the cc.programmed.payment model")
    #     self.assertEqual(action['view_mode'], 'form', "Should open the form view")
    #     self.assertEqual(action['res_id'], payment_request.id, "Should open the correct payment request")

    # def test_no_availability_button(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #         'provider': self.partner.id,
    #     })
    #     # Call the no_availability_button
    #     action = material_order.no_availability_button()

    #     # Assert that the action is correct
    #     self.assertEqual(action['type'], 'ir.actions.act_window', "Should return an action of type ir.actions.act_window")
    #     self.assertEqual(action['res_model'], 'no.availability.wizard', "Should open the no.availability.wizard model")
    #     self.assertEqual(action['view_mode'], 'form', "Should open the form view")
    #     self.assertEqual(action['target'], 'new', "Should open in a new window")
    #     self.assertEqual(action['context']['default_material_order_id'], material_order.id, "Should have the correct material order ID in the context")
    #     self.assertEqual(action['context']['default_provider_no_availability'], self.partner.id, "Should have the correct provider ID in the context")

    # def test_compute_time_to_ordered(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #     })
    #     # Test with both dates set
    #     order_request_date = date.today() - timedelta(days=5)
    #     ordered_date = date.today() - timedelta(days=2)
    #     material_order.order_request_date = order_request_date
    #     material_order.ordered_date = ordered_date
    #     material_order._compute_time_to_ordered()
    #     self.assertEqual(material_order.time_to_ordered, 3, "Should be 3 days")

    #     # Test when ordered_date is beforeorder_request_date
    #     ordered_date = date.today() - timedelta(days=5)
    #     order_request_date = date.today() - timedelta(days=2)
    #     material_order.order_request_date = order_request_date
    #     material_order.ordered_date = ordered_date
    #     material_order._compute_time_to_ordered()
    #     self.assertEqual(material_order.time_to_ordered, 0, "Should be 0 days")

    #     # Test with either date not set
    #     material_order.order_request_date = None
    #     material_order.ordered_date = date.today()
    #     material_order._compute_time_to_ordered()
    #     self.assertEqual(material_order.time_to_ordered, 0, "Should be 0 days")

    #     material_order.order_request_date = date.today()
    #     material_order.ordered_date = None
    #     material_order._compute_time_to_ordered()
    #     self.assertEqual(material_order.time_to_ordered, 0, "Should be 0 days")

    # def test_compute_time_to_rejected(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #     })
    #     # Test with both dates set
    #     ordered_date = date.today() - timedelta(days=5)
    #     rejected_date = date.today() - timedelta(days=2)
    #     material_order.ordered_date = ordered_date
    #     material_order.rejected_date = rejected_date
    #     material_order._compute_time_to_rejected()
    #     self.assertEqual(material_order.time_to_rejected, 3, "Should be 3 days")

    #     # Test when rejected_date is before ordered_date
    #     rejected_date = date.today() - timedelta(days=5)
    #     ordered_date = date.today() - timedelta(days=2)
    #     material_order.ordered_date = ordered_date
    #     material_order.rejected_date = rejected_date
    #     material_order._compute_time_to_rejected()
    #     self.assertEqual(material_order.time_to_rejected, 0, "Should be 0 days")

    #     # Test with either date not set
    #     material_order.ordered_date = None
    #     material_order.rejected_date = date.today()
    #     material_order._compute_time_to_rejected()
    #     self.assertEqual(material_order.time_to_rejected, 0, "Should be 0 days")

    #     material_order.ordered_date = date.today()
    #     material_order.rejected_date = None
    #     material_order._compute_time_to_rejected()
    #     self.assertEqual(material_order.time_to_rejected, 0, "Should be 0 days")

    # def test_compute_time_to_delivered(self):
    #     # Create a material order
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Test Order',
    #     })
    #     # Test with both dates set
    #     ordered_date = date.today() - timedelta(days=5)
    #     actual_delivery_date = date.today() - timedelta(days=2)
    #     material_order.ordered_date = ordered_date
    #     material_order.actual_delivery_date = actual_delivery_date
    #     material_order._compute_time_to_delivered()
    #     self.assertEqual(material_order.time_to_delivered, 3, "Should be 3 days")

    #     # Test when actual_delivery_date is before ordered_date
    #     actual_delivery_date = date.today() - timedelta(days=5)
    #     ordered_date = date.today() - timedelta(days=2)
    #     material_order.ordered_date = ordered_date
    #     material_order.actual_delivery_date = actual_delivery_date
    #     material_order._compute_time_to_delivered()
    #     self.assertEqual(material_order.time_to_delivered, 0, "Should be 0 days")

    #     # Test with either date not set
    #     material_order.ordered_date = None
    #     material_order.actual_delivery_date = date.today()
    #     material_order._compute_time_to_delivered()
    #     self.assertFalse(material_order.time_to_delivered, "Should be False")

    #     material_order.ordered_date = date.today()
    #     material_order.actual_delivery_date = None
    #     material_order._compute_time_to_delivered()
    #     self.assertFalse(material_order.time_to_delivered, "Should be False")


    # def test_compute_project_phase_without_project(self):
    #     material_order = self.env['pms.materials'].create({
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #         'property_id': self.env['pms.property'].create({
    #             'name': 'Another Property',
    #             'address': '456 Side St',
    #             'country_id': self.env.ref('base.us').id,
    #             'state_ids': self.env.ref('base.state_us_10').id,
    #             'city': self.city,
    #             'parcel_id': "2",
    #             'zipcode': 32810,
    #             'nunits': 1,
    #             'analytical_plan': self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id,
    #             'partner_id': self.partner.id
    #         }).id,
    #     })
    #     material_order._compute_project_phase()
    #     self.assertEqual(material_order.project_phase, 'pending', "Project phase should be 'pending' if no linked project")

    # def test_compute_total_order_amount(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     self.env['pms.materials.lines'].create({
    #         'material_order_id': material_order.id,
    #         'product': self.product.id,
    #         'quantity': 2,
    #         'amount': 50,
    #     })
    #     self.env['pms.materials.lines'].create({
    #         'material_order_id': material_order.id,
    #         'product': self.product.id,
    #         'quantity': 1,
    #         'amount': 25,
    #     })
    #     material_order._compute_total_order_amount()
    #     self.assertEqual(material_order.total_order_amount, 125.0, "Total order amount should be the sum of material line totals")

    #     material_order.material_lines = False
    #     material_order._compute_total_order_amount()
    #     self.assertEqual(material_order.total_order_amount, 0.0, "Total order amount should be 0 if no material lines")
    
    
    # def test_view_bill_linked(self):
    #     account_move = self.env['account.move'].create({
    #         'move_type': 'in_invoice',
    #         'partner_id': self.partner.id,
    #         'invoice_date': datetime.now().date(),
    #         'date': datetime.now().date(),
    #     })
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'linked_bill': account_move.id,
    #         'provider': self.partner.id,
    #         'order_creator': self.employee.id,
    #         'total_order_amount': 100.0,
    #         'name': 'Test',
    #     })
    #     action = material_order.view_bill()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['res_model'], 'account.move')
    #     self.assertEqual(action['res_id'], account_move.id)
    #     self.assertEqual(action['view_mode'], 'form')

    # @freeze_time('2025-04-25 15:00:00') # Friday 3 PM
    # def test_set_ordered_date_friday_afternoon(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     expected_monday_8am = datetime(2025, 4, 28, 8, 0, 0)
    #     self.assertEqual(material_order.set_ordered_date(), expected_monday_8am)

    # @freeze_time('2025-04-28 05:00:00') # Monday 5 AM
    # def test_set_ordered_date_monday_morning(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     now = datetime(2025, 4, 28, 5, 0, 0)
    #     self.assertEqual(material_order.set_ordered_date(), now)

    # @freeze_time('2025-04-28 10:00:00') # Monday 10 AM
    # def test_set_ordered_date_monday_late_morning(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     now = datetime(2025, 4, 28, 10, 0, 0)
    #     self.assertEqual(material_order.set_ordered_date(), now)

    # @freeze_time('2025-04-24 10:00:00') # Thursday 10 AM
    # def test_set_ordered_date_thursday(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     now = datetime(2025, 4, 24, 10, 0, 0)
    #     self.assertEqual(material_order.set_ordered_date(), now)

    # @patch('odoo.addons.pms.models.pms_materials.PMSMaterials.send_email_wait_pay')
    # def test_request_payment(self, mock_send_email):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     material_order.request_payment()
    #     self.assertEqual(material_order.order_status, 'waiting_payment', "Order status should be set to 'waiting_payment'")
    #     self.assertIsNotNone(material_order.waiting_payment_date, "Waiting payment date should be set")
    #     mock_send_email.assert_called_once()
    #     action = material_order.request_payment()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['res_model'], 'request.cc.payment.validation')
    #     self.assertEqual(action['view_mode'], 'form')
    #     self.assertEqual(action['target'], 'new')
    #     self.assertEqual(action['context']['property_owner'], material_order.property_owner.id)
    #     self.assertEqual(action['context']['company'], self.env['res.company'].search([('partner_id', '=', material_order.property_id.partner_id.id)], limit=1).id)
    #     self.assertEqual(action['context']['amount'], material_order.total_order_amount)
    #     self.assertEqual(action['context']['payment_date'], material_order.payment_date)
    #     self.assertEqual(action['context']['reference'], material_order.reference)
    #     self.assertEqual(action['context']['property_id'], material_order.property_id.id)
    #     self.assertEqual(action['context']['provider'], material_order.provider.id)
    #     self.assertEqual(action['context']['order_id'], material_order.id)

    # def test_gave_payment(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     action = material_order.gave_payment()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['res_model'], 'material.order.payment.wizard')
    #     self.assertEqual(action['view_mode'], 'form')
    #     self.assertEqual(action['target'], 'new')
    #     self.assertEqual(action['context']['active_id'], material_order.ids)
    #     self.assertEqual(action['context']['property_owner'], material_order.property_owner.id)


    # def test_go_back(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     action = material_order.go_back()
    #     self.assertEqual(action['type'], 'ir.actions.act_url')
    #     self.assertEqual(action['url'], '/web')
    #     self.assertEqual(action['target'], 'self')

    # def test_view_orders(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     action = material_order.with_context(default_order_creator=self.employee.id).view_orders()
    #     self.assertEqual(action['name'], 'Material Orders')
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['res_model'], 'pms.materials')
    #     self.assertEqual(action['target'], 'fullscreen')
    #     self.assertEqual(action['context']['default_order_creator'], self.employee.id)
    #     self.assertIn(
    #         [self.env.ref('create_material_orders.material_orders_view_kanban').id, 'kanban'],
    #         action['views']
    #     )
    #     self.assertIn(
    #         [self.env.ref('create_material_orders.material_orders_view_tree').id, 'tree'],
    #         action['views']
    #     )
    #     self.assertIn(
    #         [self.env.ref('create_material_orders.material_orders_view_calendar').id, 'calendar'],
    #         action['views']
    #     )

    # def test_delivered_not_special(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     material_order.delivered()
    #     self.assertEqual(material_order.order_status, 'delivered')

    # def test_delivered_special_not_approved(self):
    #     special_material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'special_order': True,
    #         'order_status': 'not_ordered'
    #     })
    #     with self.assertRaises(ValidationError) as cm:
    #         special_material_order.delivered()
    #     self.assertEqual(special_material_order.order_status, 'not_ordered') # Status should not change

    # def test_delivered_special_approved(self):
    #     approved_special_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'special_order': True,
    #         'special_order_approved': True,
    #     })
    #     approved_special_order.delivered()
    #     self.assertEqual(approved_special_order.order_status, 'delivered')

    # def test_return_to_not_ordered(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     action = material_order.return_to_not_ordered()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['name'], 'Not Ordered Wizard')
    #     self.assertEqual(action['res_model'], 'not.ordered.wizard')
    #     self.assertEqual(action['view_mode'], 'form')
    #     self.assertEqual(action['target'], 'new')
    #     self.assertEqual(action['context']['active_id'], material_order.id)

    # def test_open_action(self):
        # material_order = self.env['pms.materials'].create({
        #     'property_id': self.property.id,
        #     'reference': 'TEST-REF-001',
        #     'order_creator': self.employee.id,
        #     'provider': self.partner.id,
        # })
    #     action = material_order.open_action()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['name'], 'Material Orders Form')
    #     self.assertEqual(action['res_model'], 'pms.materials')
    #     self.assertEqual(action['view_mode'], 'form')
    #     self.assertEqual(action['view_id'], self.env.ref('create_material_orders.material_orders_view_form').id)
    #     self.assertEqual(action['res_id'], material_order.id)
    #     self.assertEqual(action['target'], 'current')

    # def test_confirm_order(self):
        # material_order = self.env['pms.materials'].create({
        #     'property_id': self.property.id,
        #     'reference': 'TEST-REF-001',
        #     'order_creator': self.employee.id,
        #     'provider': self.partner.id,
        # })
    #     action = material_order.with_context(default_employee=self.employee.id).confirm_order()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['name'], 'Confirm Orders Wizard')
    #     self.assertEqual(action['res_model'], 'confirm.orders.wizard')
    #     self.assertEqual(action['view_mode'], 'form')
    #     self.assertEqual(action['target'], 'new')
    #     self.assertEqual(action['context']['order_id'], material_order.id)
    #     self.assertEqual(action['context']['material_lines'], material_order.material_lines.ids)
    #     self.assertEqual(action['context']['default_employee'], self.employee.id)

    # def test_send_message_team(self):
        # material_order = self.env['pms.materials'].create({
        #     'property_id': self.property.id,
        #     'reference': 'TEST-REF-001',
        #     'order_creator': self.employee.id,
        #     'provider': self.partner.id,
        # })
    #     action = material_order.send_message_team()
    #     self.assertEqual(action['type'], 'ir.actions.act_window')
    #     self.assertEqual(action['name'], 'Send Message to Team')
    #     self.assertEqual(action['res_model'], 'send.order.message.wizard')
    #     self.assertEqual(action['view_mode'], 'form')
    #     self.assertEqual(action['target'], 'new')
    #     self.assertEqual(action['context']['active_id'], material_order.id)
    #     self.assertEqual(action['context']['model'], 'pms.materials')

    # def test_compute_escrow_account(self):
    #     # Create a material order with an escrow company
    #     """material_order = self.env['pms.materials'].create({'property_id': self.property.id, 'escrow_company': self.company.id})
    #     escrow_account = self.env['account.account'].create({
    #         'name': 'Test Escrow Account',
    #         'code': '1815202',
    #         'company_id': self.company.id
    #     })
    #     material_order._compute_escrow_account()
    #     self.assertEqual(material_order.escrow_account.id, escrow_account.id, "Should find and assign the escrow account")"""

    #     # Create a material order without an escrow company
    #     material_order_no_escrow = self.env['pms.materials'].create({'property_id': self.property.id})
    #     material_order_no_escrow._compute_escrow_account()
    #     self.assertFalse(material_order_no_escrow.escrow_account, "Should be False when no escrow company is set")

    #     # Test when the escrow account doesn't exist
    #     company2 = self.env['res.company'].create({'name': 'Company B'})
    #     material_order_no_account = self.env['pms.materials'].create({'property_id': self.property.id, 'escrow_company': company2.id})
    #     material_order_no_account._compute_escrow_account()
    #     self.assertFalse(material_order_no_account.escrow_account, "Should be False when the account doesn't exist")

    # def test_compute_project_phase_with_project(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     material_order._compute_project_phase()
    #     self.assertEqual(material_order.project_phase, 'coc', "Project phase should be taken from the linked project")


####################################################################################################################################################################################################

    # def test_view_bill_not_linked(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'provider': self.partner.id,
    #         'order_creator': self.employee.id,
    #         'total_order_amount': 100.0,
    #         'name': 'Test',
    #         'linked_bill': False
    #     })
    #     with self.assertRaises(UserError):
    #         material_order.view_bill()

    # def test_create_request_payment(self):
    
    #     # MUST FIND _compute_analytics_accounts TO SEE THE PROBLEM
    
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     initial_payment_request_count = self.env['cc.programmed.payment'].search_count([('material_order', '=', material_order.id)])
    #     material_order.create_request_payment(company=self.company.id)
    #     final_payment_request_count = self.env['cc.programmed.payment'].search_count([('material_order', '=', material_order.id)])
    #     self.assertEqual(final_payment_request_count, initial_payment_request_count + 1, "A new payment request should be created")
    #     self.assertIsNotNone(material_order.linked_payment_request, "Linked payment request ID should be set")
    #     new_payment_request = self.env['cc.programmed.payment'].browse(material_order.linked_payment_request)
    #     self.assertEqual(new_payment_request.requested_by.id, material_order.order_creator.id)
    #     self.assertEqual(new_payment_request.provider.id, material_order.provider.id)
    #     self.assertEqual(new_payment_request.amount, material_order.total_order_amount)
    #     self.assertEqual(new_payment_request.company.id, self.company.id)
    #     self.assertEqual(new_payment_request.concept, material_order.name)
    #     self.assertEqual(new_payment_request.properties.ids, [material_order.property_id.id])
    #     self.assertEqual(new_payment_request.material_order.id, material_order.id)
    #     self.assertEqual(new_payment_request.request_type, 'material')
    #     self.assertEqual(new_payment_request.bill_id.id, material_order.linked_bill.id)
    #     self.assertTrue(new_payment_request.has_bill)
        
    # def test_create_payment_after_invoice(self):
    
    # # You can't create a new payment without an outstanding payments/receipts account
    
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'reference': 'TEST-REF-001',
    #         'order_creator': self.employee.id,
    #         'provider': self.partner.id,
    #     })
    #     material_order.company_third_party = self.company
    #     initial_payment_count = self.env['account.payment'].search_count([('ref', '=', material_order.payment_method or material_order.name)])
    #     material_order.create_payment_after_invoice()
    #     final_payment_count = self.env['account.payment'].search_count([('ref', '=', material_order.payment_method or material_order.name)])
    #     self.assertEqual(final_payment_count, initial_payment_count + 1, "A new payment should be created")
    #     self.assertIsNotNone(material_order.linked_payment, "Linked payment ID should be set")
    #     new_payment = self.env['account.payment'].browse(material_order.linked_payment)
    #     self.assertEqual(new_payment.partner_id.id, material_order.provider.id)
    #     self.assertEqual(new_payment.company_id.id, material_order.company_third_party.id)
    #     self.assertEqual(new_payment.payment_type, 'outbound')
    #     self.assertEqual(new_payment.partner_type, 'supplier')
    #     self.assertEqual(new_payment.amount, material_order.total_order_amount)
    #     self.assertEqual(new_payment.ref, material_order.payment_method or material_order.name)
    #     self.assertEqual(new_payment.state, 'posted') # action_post should set state to 'posted'
         

    # def test_send_email_to_no_addresses(self):
    #     material_order = self.env['pms.materials'].create({
    #         'property_id': self.property.id,
    #         'name': 'Special Order Test',
    #         'special_order': True,
    #         'special_order_approved': False,
    #     })
    #     result = material_order._send_email_to([], self.html_content)
    #     self.assertEqual(result['type'], 'ir.actions.act_window')
    #     self.assertEqual(result['name'], 'No Email Wizard')
    #     self.assertEqual(result['res_model'], 'no.email.wizard')
    #     self.assertEqual(result['view_mode'], 'form')
    #     self.assertEqual(result['target'], 'new')
    #     self.assertEqual(result['context'], {'order_id': material_order.id})

