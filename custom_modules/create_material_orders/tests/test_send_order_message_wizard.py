from odoo.tests import common
from odoo import exceptions

class TestSendOrderMessageWizard(common.TransactionCase):

    def setUp(self):
        super().setUp()
        self.sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
        })
        self.wizard_model = self.env['send.order.message.wizard']



    def test_send_message_success(self):
        message_body = "Test message."
        wizard = self.wizard_model.with_context({
            'active_id': self.sale_order.id,
            'model': 'sale.order',
        }).create({
            'message': message_body,
        })
        wizard.send_message()
        self.assertTrue(self.sale_order.message_ids, "No messages found.")
        self.assertEqual(self.sale_order.message_ids[0].body, '<p>Test message.</p>', "Message content mismatch.")



    def test_send_message_missing_model(self):
        wizard = self.wizard_model.with_context({
            'active_id': self.sale_order.id,
        }).create({
            'message': "Message without model.",
        })
        with self.assertRaises(ValueError) as cm:
            wizard.send_message()
        self.assertEqual(str(cm.exception), "Model name is missing from the context")



    def test_send_message_invalid_active_id(self):
        wizard = self.wizard_model.with_context({
            'active_id': 999999,
            'model': 'sale.order',
        }).create({
            'message': "Message to invalid ID.",
        })
        with self.assertRaises(exceptions.MissingError):
            wizard.send_message()