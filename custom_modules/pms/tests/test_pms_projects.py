from odoo.tests.common import TransactionCase
from datetime import timedelta
from odoo import api, models, fields

class TestPmsProjects(TransactionCase):
    
    def setUp(self):
        super().setUp()

        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.city = self.env['pms.cities'].create({'name': 'Orlando'})
        florida_state = self.env.ref('base.state_us_10')
        self.county = self.env['pms.county'].create({'name': 'Orange County', 'state': florida_state.id})
        self.country = self.env['res.country'].search([], limit=1)
        self.house_model = self.env['pms.housemodels'].create({'name': '1250'})
        self.analytic_plan = self.env['account.analytic.plan'].create({'name': 'Test Properties Plan'})
        self.property = self.env['pms.property'].create({
            'address': '789 Sunset Blvd',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': self.city.id,
            'county': self.county.id,
            'house_model': self.house_model.id,
            'parcel_id': "1",
            'country_id': self.country.id,
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.analytic_plan.id,
            'partner_id': self.partner.id
        })
        self.employee = self.env['hr.employee'].create({'name': 'Test Employee'})
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
        })

    def test_compute_last_visit_day(self):

        # 1. No visits
        self.project._compute_last_visit_day()
        self.assertFalse(self.project.last_visit_day)

        # 2. One visit
        visit1 = self.env['pms.visit.days'].create({
            'property_name': self.project.address.id,
            'visit_date': fields.Date.today()
        })
        self.project._compute_last_visit_day()
        self.assertEqual(self.project.last_visit_day, visit1.visit_date)

        # 3. Multiple visits
        visit2 = self.env['pms.visit.days'].create({
            'property_name': self.project.address.id,
            'visit_date': fields.Date.today() - timedelta(days=1)
        })
        self.project._compute_last_visit_day()
        self.assertEqual(self.project.last_visit_day, visit1.visit_date)  # Should be the latest

    def test_update_days_since_last_visit(self):
        self.env['pms.visit.days'].create({
            'property_name': self.project.address.id,
            'visit_date': fields.Date.today() - timedelta(days=5)
        })

        self.project._update_days_since_last_visit()
    
    def test_update_status_construction(self):

        # 1. new_status in ["cop1", "cop2", "cop3", "cop4", "coc", "completed"]
        self.project.update_status_construction('cop1')
        self.assertEqual(self.project.status_construction, 'cop1')
        self.assertTrue(self.project.construction_started)

        self.project.update_status_construction('coc')
        self.assertEqual(self.project.status_construction, 'coc')
        self.assertTrue(self.project.construction_started)

        # 2. new_status == "cop" and from_activity == False
        with self.env.cr.savepoint():
            self.project.update_status_construction('cop')
            self.assertEqual(self.project.status_construction, 'cop')
            self.assertFalse(self.project.construction_started)

        # 3. new_status == "cop" and from_activity == True (via context)
        with self.env.cr.savepoint():
            self.project = self.project.with_context(from_activity=True)
            self.project.update_status_construction('cop')
            self.assertEqual(self.project.status_construction, 'cop')
            self.assertFalse(self.project.construction_started)

        # 4. new_status not in the above cases
        self.project.update_status_construction('pending')
        self.assertEqual(self.project.status_construction, 'pending')
        self.assertFalse(self.project.construction_started)
    def test_compute_construction_started(self):

        # 1. status_construction in ["cop1", "cop2", "cop3", "cop4", "coc", "completed"]
        self.project.status_construction = 'cop1'
        self.project._compute_construction_started()
        self.assertTrue(self.project.construction_started)

        self.project.status_construction = 'coc'
        self.project._compute_construction_started()
        self.assertTrue(self.project.construction_started)

        # 2. status_construction == "cop" and from_activity == False
        self.project.status_construction = 'cop'
        self.project.from_activity = False
        self.project._compute_construction_started()
        self.assertFalse(self.project.construction_started)

        # 3. status_construction == "cop" and from_activity == True
        self.project.status_construction = 'cop'
        self.project.from_activity = True
        self.project._compute_construction_started()
        self.assertTrue(self.project.construction_started)

        # 4. status_construction not in the above cases
        self.project.status_construction = 'pending'
        self.project._compute_construction_started()
        self.assertFalse(self.project.construction_started)
    
    def test_property_coc(self):

        # 1. status_construction = 'pending'
        self.project.status_construction = 'pending'
        self.project.property_coc()
        self.assertEqual(self.project.address.status_property, 'draft')

        # 2. status_construction in ("pip", "pps", "epp", "ppa", "cop", "cop1", "cop2", "cop3", "cop4")
        self.project.status_construction = 'pip'
        self.project.property_coc()
        self.assertEqual(self.project.address.status_property, 'construction')

        self.project.status_construction = 'cop'
        self.project.property_coc()
        self.assertEqual(self.project.address.status_property, 'construction')

        # 3. status_construction in ("coc", "completed")
        self.project.status_construction = 'coc'
        self.project.property_coc()
        self.assertEqual(self.project.address.status_property, 'coc')

        self.project.status_construction = 'completed'
        self.project.property_coc()
        self.assertEqual(self.project.address.status_property, 'coc')
    
    def test_set_available(self):
        self.project.set_available()
        self.assertTrue(self.project.address.available)

    def test_set_unavailable(self):
        self.project.set_unavailable()
        self.assertFalse(self.project.address.available)

    def test_set_available_for_rent(self):
        self.project.set_available_for_rent()
        self.assertTrue(self.project.address.available_for_rent)

    def test_set_unavailable_for_rent(self):
        self.project.set_unavailable_for_rent()
        self.assertFalse(self.project.address.available_for_rent)
        
    """View tests"""
    
    def test_get_summary_view(self):
        
        action = self.project.get_summary_view()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'pms.project.summary')
        self.assertEqual(action['view_mode'], 'tree')
        self.assertIn('property_project', action['context'])
        self.assertIn('project_route', action['context'])

    def test_get_phase_times(self):
        
        action = self.project.get_phase_times()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'pms.phase.time')
        self.assertEqual(action['view_mode'], 'tree')
        self.assertIn('property_project', action['context'])

    def test_open_visit_wizard(self):
        
        action = self.project.open_visit_wizard()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'visit.days.wizard')
        self.assertEqual(action['view_mode'], 'form')
        self.assertIn('active_ids', action['context'])

    def test_open_visit_project_wizard(self):
        
        action = self.project.open_visit_project_wizard()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'visit.day.project.wizard')
        self.assertEqual(action['view_mode'], 'form')
        self.assertIn('active_ids', action['context'])

    def test_open_planned_visit_wizard(self):
        
        action = self.project.open_planned_visit_wizard()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'planned.visit.days.wizard')
        self.assertEqual(action['view_mode'], 'form')
        self.assertIn('active_ids', action['context'])

    def test_action_update_house_model(self):
        
        action = self.project.action_update_house_model()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'pms.projects.update.house.model')
        self.assertEqual(action['view_mode'], 'form')
        self.assertEqual(action['target'], 'new')



class TestPmsProjectsLoanExpiration(TransactionCase):
    def setUp(self):
        super().setUp()

        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.city = self.env['pms.cities'].create({'name': 'Orlando'})
        florida_state = self.env.ref('base.state_us_10')
        self.county = self.env['pms.county'].create({'name': 'Orange County', 'state': florida_state.id})
        self.country = self.env['res.country'].search([], limit=1)
        self.house_model = self.env['pms.housemodels'].create({'name': '1250'})
        self.analytic_plan = self.env['account.analytic.plan'].create({'name': 'Test Properties Plan'})
        self.property = self.env['pms.property'].create({
            'address': '789 Sunset Blvd',
            'country_id': self.env.ref('base.us').id,
            'state_ids': self.env.ref('base.state_us_10').id,
            'city': self.city.id,
            'county': self.county.id,
            'house_model': self.house_model.id,
            'parcel_id': "1",
            'country_id': self.country.id,
            'zipcode': 32809,
            'nunits': 1,
            'analytical_plan': self.analytic_plan.id,
            'partner_id': self.partner.id
        })
        self.employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        self.project_routes_template = self.env['pms.projects.routes.templates'].create({'name': 'New Ocala Route'})
        # Create a line for the route template and associate it
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
        })
    def test_compute_loan_expiration(self):
        # Create a pms.loans record
        loan = self.env['pms.loans'].create({
            'property_address': self.property.id,
            'maturity_date': fields.Date.add(fields.Date.today(), months=6),
            'loan_type': 'construction',
            'exit_status': 'ongoing',
        })

        self.assertFalse(self.project.loan_expiration)
        self.project._compute_loan_expiration()
        self.assertEqual(self.project.loan_expiration, loan.maturity_date) # Expect the maturity date

        # Update the loan's maturity date to the past
        loan.maturity_date = fields.Date.subtract(fields.Date.today(), months=1)
        # We might need to trigger a recomputation on the self.project
        self.project._compute_loan_expiration()
        self.assertEqual(self.project.loan_expiration, loan.maturity_date) # Expect the past maturity date
        
# class TestPmsProjectsUpdateInvoicesCustodial(TransactionCase):
    
#     def setUp(self):
#         super().setUp()

#         self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
#         self.city = self.env['pms.cities'].create({'name': 'Orlando'})
#         florida_state = self.env.ref('base.state_us_10')
#         self.county = self.env['pms.county'].create({'name': 'Orange County', 'state': florida_state.id})
#         self.country = self.env['res.country'].search([], limit=1)
#         self.house_model = self.env['pms.housemodels'].create({'name': '1250'})
#         self.analytic_plan = self.env['account.analytic.plan'].create({'name': 'Test Properties Plan'})
#         self.property = self.env['pms.property'].create({
#             'address': '789 Sunset Blvd',
#             'country_id': self.env.ref('base.us').id,
#             'state_ids': self.env.ref('base.state_us_10').id,
#             'city': self.city.id,
#             'county': self.county.id,
#             'house_model': self.house_model.id,
#             'parcel_id': "1",
#             'country_id': self.country.id,
#             'zipcode': 32809,
#             'nunits': 1,
#             'analytical_plan': self.analytic_plan.id,
#             'partner_id': self.partner.id
#         })
#         self.employee = self.env['hr.employee'].create({'name': 'Test Employee'})
#         self.project_routes_template = self.env['pms.projects.routes.templates'].create({'name': 'New Ocala Route'})
#         self.template_line = self.env['pms.projects.routes.templates.lines'].create({
#             'name': 'OC Engineering Fee',
#             'route_header': self.project_routes_template.id,
#             'sequence': 1,
#             'phase': 'pip'
#         })
#         self.project = self.env['pms.projects'].create({
#             'address': self.property.id,
#             'project_routes': self.project_routes_template.id,
#             'project_manager': self.employee.id,
#             'superintendent': self.employee.id,
#             'zone_coordinator': self.employee.id,
#             'visit_day': 'monday',
#             'second_visit_day': 'tuesday',
#         })

#         self.company = self.env['res.company'].create({'name': 'TestCo', 'partner_id': self.partner.id})
#         self.account = self.env['account.account'].search([('code', '=', '2009')], limit=1)

#         self.account_move = self.env['account.move'].create({
#             'move_type': 'out_invoice',
#             'partner_id': self.partner.id,
#             'invoice_line_ids': [(0, 0, {
#                 'name': 'Test Invoice Line',
#                 'quantity': 1,
#                 'price_unit': 100,
#                 'account_id': self.account.id,
#                 'analytic_distribution': {str(self.analytic_plan.id): 100.0}
#             })]
#         })
#         self.account_move_line = self.env['account.move.line'].create({
#             'move_id': self.account_move.id,
#             'account_id': self.account.id,
#             'analytic_distribution': {str(self.analytic_plan.id): 100.0},
#             'debit': 100.0,
#             'credit': 0.0,
#         })

#     def test_update_invoices_custodial_money(self):

#         self.account_move_line = self.env['account.move.line'].create({
#             'move_id': self.account_move.id,
#             'analytic_distribution': {str(self.analytic_plan.id): 100.0},
#             'account_id': self.account.id,
#             'debit': 0.0,
#             'credit': 0.0,
#         })

#         self.project.custodial_money = True
#         self.project.on_off_hold = False
#         self.project._update_invoices_custodial_money()
#         self.assertEqual(self.account_move.invoice_type, 'escrow')

#         self.project.custodial_money = True
#         self.project.on_off_hold = True
#         self.project._update_invoices_custodial_money()
#         self.assertEqual(self.account_move.invoice_type, 'hold')

#         self.project.custodial_money = False
#         self.project.on_off_hold = True
#         self.project._update_invoices_custodial_money()
#         self.assertEqual(self.account_move.invoice_type, 'hold')

#         self.project.custodial_money = False
#         self.project.on_off_hold = False
#         self.project._update_invoices_custodial_money()
#         self.assertEqual(self.account_move.invoice_type, '1stparty')

#         self.project.custodial_money = False
#         self.project.on_off_hold = False
#         self.company.unlink()
#         self.project._update_invoices_custodial_money()
#         self.assertEqual(self.account_move.invoice_type, '3rdparty')

#         self.account_move_2 = self.env['account.move'].create({
#             'move_type': 'out_invoice',
#             'partner_id': self.partner.id,
#             'invoice_line_ids': [
#                 (0, 0, {'name': 'Line 1', 'quantity': 1, 'price_unit': 100, 'analytic_distribution': {str(self.analytic_plan.id): 100.0}}),
#                 (0, 0, {'name': 'Line 2', 'quantity': 1, 'price_unit': 100, 'analytic_distribution': {str(self.analytic_plan.id): 100.0, str(self.env['account.analytic.plan'].create({'name': 'Test Plan'}).id): 100.0}}),
#             ]
#         })
#         self.project._update_invoices_custodial_money()
#         self.assertEqual(self.account_move_2.invoice_type, 'various')