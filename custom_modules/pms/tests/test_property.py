from odoo import fields, Command
from odoo.tests.common import TransactionCase, HttpCase, tagged, Form
from odoo.exceptions import ValidationError
from datetime import datetime, date, timedelta

class TestPropertyOwnThird(TransactionCase):
    def test_compute_own_third_property_owned(self):
        partner = self.env['res.partner'].create({'name': 'Partner A'})
        company = self.env['res.company'].create({'name': 'TestCo', 'partner_id': partner.id})
        city = self.env['pms.cities'].search([("name", "=", "Orlando")]).id
        property_address = self.env['pms.property'].create({
            'address': '123 Main St',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': city,
            'parcel_id': "1",
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id,
            'partner_id': partner.id
        })
        property_address._compute_own_third()
        self.assertEqual(property_address.own_third, 'own')

    def test_compute_own_third_third_party(self):
        city = self.env['pms.cities'].search([("name", "=", "Orlando")]).id
        partner = self.env['res.partner'].create({'name': 'Partner B'})
        property_address = self.env['pms.property'].create({
            'address': '456 Elm St',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': city,
            'parcel_id': "1",
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id,
            'partner_id': partner.id
        })
        property_address._compute_own_third()
        self.assertEqual(property_address.own_third, 'third')

    def test_without_property_owner(self):
        city = self.env['pms.cities'].search([("name", "=", "Orlando")]).id
        property_address = self.env['pms.property'].create({
            'address': '456 Elm St no owner',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': city,
            'parcel_id': "1",
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id,
        })
        property_address._compute_own_third()
        self.assertEqual(property_address.own_third, 'third')

class TestPMSPropertySuperintendent(TransactionCase):
    def setUp(self):
        super().setUp()
        self.city = self.env['pms.cities'].search([("name", "=", "Orlando")]).id
        self.partner = self.env['res.partner'].create({'name': 'Owner'})
        self.employee = self.env['hr.employee'].create({'name': 'John Doe'})

        self.property = self.env['pms.property'].create({
            'address': '789 Sunset Blvd',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': self.city,
            'parcel_id': "1",
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id,
            'partner_id': self.partner.id
        })

    def test_superintendent_is_set_from_project(self):
        self.env['pms.projects'].create({
            'address': self.property.id,
            'superintendent': self.employee.id
        })
        self.property._compute_superintendent()
        self.assertEqual(self.property.superintendent, self.employee)

    def test_superintendent_is_false_if_none(self):
        self.env['pms.projects'].create({
            'address': self.property.id,
            'superintendent': False
        })
        self.property._compute_superintendent()
        self.assertFalse(self.property.superintendent)

    def test_superintendent_is_false_if_no_project(self):
        self.property._compute_superintendent()
        self.assertFalse(self.property.superintendent)

 
class TestPMSPropertySimpleMethods(TransactionCase):
    def setUp(self):
        super().setUp()
        self.city = self.env['pms.cities'].search([("name", "=", "Orlando")]).id
        self.partner = self.env['res.partner'].create({'name': 'Test Owner'})
        self.property = self.env['pms.property'].create({
            'address': '789 Sunset Blvd',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': self.city,
            'parcel_id': "1",
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id,
            'partner_id': self.partner.id
        })


    def test_set_available_sets_true(self):
        self.property.set_available()
        self.assertTrue(self.property.available)

    def test_set_unavailable_sets_false(self):
        self.property.set_unavailable()
        self.assertFalse(self.property.available)

    def test_set_available_for_rent_sets_true(self):
        self.property.set_available_for_rent()
        self.assertTrue(self.property.available_for_rent)

    def test_set_unavailable_for_rent_sets_false(self):
        self.property.set_unavailable_for_rent()
        self.assertFalse(self.property.available_for_rent)

    def test_to_coc_sets_status(self):
        self.property.to_coc()
        self.assertEqual(self.property.status_property, 'coc')

class TestPMSPropertyFullAddress(TransactionCase):
    def setUp(self):
        super().setUp()
        self.country = self.env.ref('base.us')
        self.state = self.env.ref('base.state_us_10')
        self.city = self.env['pms.cities'].create({'name': 'Miami'})
        self.partner = self.env['res.partner'].create({'name': 'Owner'})
        self.plan = self.env['account.analytic.plan'].search([('name', '=', 'Properties')]).id

    def create_property(self, **kwargs):
        default_vals = {
            'address': '123 Ocean Dr',
            'country_id': self.country.id,
            'state_ids': self.state.id,
            'city': self.city.id,
            'parcel_id': "1",
            'zipcode': 33139,
            'nunits': 1,
            'partner_id': self.partner.id,
            'analytical_plan': self.plan,
        }
        default_vals.update(kwargs)
        return self.env['pms.property'].create(default_vals)

    def test_full_address_computed_correctly(self):
        prop = self.create_property()
        prop._property_full_address()
        self.assertEqual(prop.name, "123 Ocean Dr Miami, Florida 33139")  

    def test_missing_zipcode_sets_blank_name(self):
        prop = self.create_property(zipcode=False)
        prop._property_full_address()
        self.assertEqual(prop.name, " ")

class TestPMSPropertyAnalytical(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Test Owner'})
        self.plan = self.env['account.analytic.plan'].search([('name', '=', 'Properties')])
        self.state = self.env.ref('base.state_us_10')
        self.city = self.env['pms.cities'].create({'name': 'Orlando'})

        self.property = self.env['pms.property'].create({
            'address': '456 Palm St',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.state.id,
            'city': self.city.id,
            'zipcode': 32801,
            'nunits': 1,
            'parcel_id': 'PCL-009',
            'partner_id': self.partner.id,
            'analytical_plan': self.plan.id
        })

        # compute name (since _property_analytical depends on it)
        self.property._property_full_address()

    def test_creates_analytic_account(self):
        analytic_id = self.property._property_analytical()
        account = self.env['account.analytic.account'].browse(analytic_id)
        expected_name = f"{self.property.name} {self.property.parcel_id} {self.partner.name}"

        self.assertEqual(account.name, expected_name)
        self.assertEqual(account.plan_id, self.plan)
        self.assertEqual(account.partner_id, self.partner)
        self.assertFalse(account.company_id)
        self.assertEqual(self.property.analytical_account.id, analytic_id) 

    def test_raises_error_when_parcel_id_missing(self):
        self.property.parcel_id = False
        with self.assertRaises(ValidationError, msg="Please set a parcel id"):
            self.property._property_analytical()

    def test_raises_error_when_partner_missing(self):
        self.property.partner_id = False
        with self.assertRaises(ValidationError):
            self.property._property_analytical()

class TestPMSPropertyOnchange(TransactionCase):

    def setUp(self):
        super().setUp()
        self.country = self.env.ref('base.us')
        self.state = self.env.ref('base.state_us_10')
        self.city = self.env['pms.cities'].search([("name", "=", "Orlando")])
        self.plan = self.env['account.analytic.plan'].search([('name', '=', 'Properties')])
        self.partner = self.env['res.partner'].create({'name': 'Original Owner'})
        self.county = self.env['pms.county'].search([("name", "=", "Orange County")])

        self.property = self.env['pms.property'].create({
            'address': '101 Main St',
            'country_id': self.country.id,
            'state_ids': self.state.id,
            'city': self.city.id,
            'zipcode': 32801,
            'nunits': 1,
            'parcel_id': 'PCL-001',
            'partner_id': self.partner.id,
            'analytical_plan': self.plan.id,
        })

        self.property._property_full_address()
        self.property._property_analytical()

    def test_onchange_property_analytical_updates_account(self):
        new_partner = self.env['res.partner'].create({'name': 'New Owner'})
        self.property.partner_id = new_partner
        self.property.name = "Updated Full Address"
        self.property._change_property_analytical()

        expected_name = f"{self.property.name} {self.property.parcel_id} {new_partner.name}"
        self.assertEqual(self.property.analytical_account.name, expected_name)
        self.assertEqual(self.property.analytical_account.partner_id, new_partner)

    def test_onchange_city_sets_state_and_county(self):
        self.property.city = self.city
        self.property._onchange_city()

        self.assertEqual(self.property.state_ids, self.state)
        self.assertEqual(self.property.county, self.county)

    def test_onchange_state_sets_country(self):
        self.property.state_ids = self.state
        self.property._onchange_state()

        self.assertEqual(self.property.country_id, self.country)


class TestPMSPropertyStatusTransitions(TransactionCase):

    def setUp(self):
        super().setUp()
        self.country = self.env.ref('base.us')
        self.city = self.env['pms.cities'].search([("name", "=", "Orlando")])
        self.plan = self.env['account.analytic.plan'].search([('name', '=', 'Properties')])
        self.state = self.env.ref('base.state_us_10')
        self.partner = self.env['res.partner'].create({'name': 'Owner'})
        
        self.property = self.env['pms.property'].create({
            'address': '100 Test Lane',
            'country_id': self.country.id,
            'state_ids': self.state.id,
            'city': self.city.id,
            'zipcode': 73301,
            'nunits': 1,
            'parcel_id': 'TX-001',
            'partner_id': self.partner.id,
            'analytical_plan': self.plan.id,
        })

        self.property._property_full_address()

    def test_to_construction_with_account(self):
        self.property._property_analytical()
        self.property.to_construction()
        self.assertEqual(self.property.status_property, 'construction')
        self.assertTrue(self.property.analytical_account)

    def test_to_construction_without_account_creates_account(self):
        self.property.to_construction()
        self.assertEqual(self.property.status_property, 'construction')
        self.assertTrue(self.property.analytical_account)

    def test_to_rent_with_account(self):
        self.property._property_analytical()
        self.property.to_rent()
        self.assertEqual(self.property.status_property, 'rented')
        self.assertTrue(self.property.analytical_account)

    def test_to_rent_without_account_creates_account(self):
        self.property.to_rent()
        self.assertEqual(self.property.status_property, 'rented')
        self.assertTrue(self.property.analytical_account)

    def test_to_draft_with_account(self):
        self.property.to_construction()
        self.property.to_draft()
        self.assertEqual(self.property.status_property, 'draft')
        self.assertFalse(self.property.analytical_account)

    def test_to_draft_with_account(self):
        self.property.to_draft()
        self.assertEqual(self.property.status_property, 'draft')
        self.assertFalse(self.property.analytical_account)

    def test_put_on_hold_auto_creates_history(self):
        self.property.put_on_hold(auto=True)
        self.assertTrue(self.property.on_hold)

        history = self.env['pms.on.hold.history'].search([('property_name', '=', self.property.id), ('date', '=', datetime.today())])
        self.assertTrue(history)
        self.assertEqual(history.property_name.id, self.property.id)
        self.assertTrue(history.mail_notification)

    def test_put_on_hold_returns_wizard_action(self):
        action = self.property.put_on_hold(auto=False)
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'on.hold.wizard')
        self.assertEqual(action['context']['default_property_id'], self.property.id)

    def test_put_off_hold_auto_updates_status_and_history(self):
        self.property.on_hold = True
        self.history = self.env['pms.on.hold.history'].create({
            'property_name': self.property.id,
            'date': datetime.now() - timedelta(days=1),
            'mail_notification': True,
            'previous_status': 'cop4',
            'comments': '',
            'jennys_calls': False,
        })
        self.property.put_off_hold(auto=True)
        self.assertFalse(self.property.on_hold)


        history = self.history
        self.assertIsNotNone(history.hold_end_date)
        self.assertEqual(history.off_hold_reason, "Closed automatically by odoo")

    def test_put_off_hold_returns_wizard_action(self):
        action = self.property.put_off_hold(auto=False)
        self.assertIsInstance(action, dict)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'off.hold.wizard')
        self.assertEqual(action['context']['default_property_id'], self.property.id)
