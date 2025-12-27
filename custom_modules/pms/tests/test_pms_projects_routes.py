from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from unittest.mock import patch

class TestPmsProjectsRoutes(TransactionCase):
    def setUp(self):
        super().setUp()
        self.project_routes_template = self.env['pms.projects.routes.templates'].create({'name': 'New Ocala Route'})
        self.template_line = self.env['pms.projects.routes.templates.lines'].create({
            'name': 'OC Engineering Fee',
            'route_header': self.project_routes_template.id,
            'sequence': 1,
            'phase': 'pip'
        })
        self.partner = self.env['res.partner'].create({'name': 'Test Partner'})
        self.employee = self.env['hr.employee'].create({'name': 'Test Employee'})
        self.city = self.env['pms.cities'].create({'name': 'Orlando'})
        self.florida_state = self.env.ref('base.state_us_10')
        self.county = self.env['pms.county'].create({'name': 'Orange County', 'state': self.florida_state.id})
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
        self.project = self.env['pms.projects'].create({
            'address': self.property.id,
            'project_routes': self.project_routes_template.id,
            'project_manager': self.employee.id,
            'superintendent': self.employee.id,
            'zone_coordinator': self.employee.id,
            'visit_day': 'monday',
            'second_visit_day': 'tuesday',
            'status_construction': 'ppa',
        })
        self.product = self.env['product.product'].create({'name': 'Test Product'})
        self.project_route = self.env['pms.projects.routes'].create({
            'project_property': self.project.id,
            'name': self.template_line.id,
            'product': self.product.id,
            'vendor': self.partner.id,
        })

        
    def test_create_pms_projects_routes(self):
        self.product = self.env['product.product'].create({'name': 'Test Product'})
        new_property = self.env['pms.property'].create({
            'address': '789 Sunset Blvd 2',
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
        new_project = self.env['pms.projects'].create({
            'address': new_property.id,
            'project_routes': self.project_routes_template.id,
            'project_manager': self.employee.id,
            'superintendent': self.employee.id,
            'zone_coordinator': self.employee.id,
            'visit_day': 'monday',
            'second_visit_day': 'tuesday',
        })
        new_route = self.env['pms.projects.routes'].create({
            'project_property': new_project.id,
            'name': self.template_line.id,
            'product': self.product.id,
            'vendor': self.partner.id,
        })
        self.assertIsInstance(new_route, self.env['pms.projects.routes'].__class__, "Record not created")
        self.assertEqual(new_route.project_property, new_project, "Project property not assigned correctly")
        self.assertEqual(new_route.name, self.template_line, "Activity name not assigned correctly")

    def test_onchange_name(self):
        """Test the _onchange_name method."""

        new_partner = self.env['res.partner'].create({'name': 'New Test Partner'})
        self.template_line.vendor = new_partner

        route = self.env['pms.projects.routes'].new({'name': self.template_line.id})
        route._onchange_name()

        self.assertEqual(route.vendor, new_partner, "Vendor not updated")
    
    def test_check_job_constraint(self):
        """Test the check_job constraint."""

        with self.assertRaises(ValidationError):
            self.env['pms.projects.routes'].create({
                'project_property': self.project.id,
                'name': self.template_line.id,
                'product': self.product.id,
                'vendor': self.partner.id,
            })
            self.env['pms.projects.routes'].create({
                'project_property': self.project.id,
                'name': self.template_line.id,
                'product': self.product.id,
                'vendor': self.partner.id,
            })
    
    def test_check_critical_activity_completion(self):
        """Test the _check_critical_activity_completion constraint."""
        new_route_template = self.env['pms.projects.routes.templates'].create({'name': 'New Test Route Template'})

        alert_line = self.env['pms.projects.routes.templates.lines'].create({
            'route_header': new_route_template.id,
            'name': 'Alert Activity',
            'sequence': 0,
            'alert': True,
        })

        with self.assertRaises(ValidationError):
            self.env['pms.projects.routes'].create({
                'project_property': self.project.id,
                'name': self.template_line.id,
            })

    def test_check_project_on_hold(self):
        """Test the _check_project_on_hold constraint."""
        self.project.on_off_hold = True
        with self.assertRaises(ValidationError):
            self.env['pms.projects.routes'].create({
                'project_property': self.project.id,
                'name': self.template_line.id,
            })

    def test_end_start_dependency(self):
        """Test the _end_start computed field."""
        now = datetime.now()
        order_date = now - timedelta(days=5)
        end_date = now + timedelta(days=10)
        new_property = self.env['pms.property'].create({
            'address': '789 Sunset Blvd 2',
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
        new_project = self.env['pms.projects'].create({
            'address': new_property.id,
            'project_routes': self.project_routes_template.id,
            'project_manager': self.employee.id,
            'superintendent': self.employee.id,
            'zone_coordinator': self.employee.id,
            'visit_day': 'monday',
            'second_visit_day': 'tuesday',
            'status_construction': 'ppa',
        })
        route = self.env['pms.projects.routes'].create({
            'project_property': new_project.id,
            'name': self.template_line.id,
            'order_date': order_date,
            'end_date': end_date,
            'start_date': now
        })
        self.assertEqual(route.time_spent, 15, "Time spent is incorrect")

    def test_duration_time_spent_dependency(self):
        """Test the _duration_time_spent computed field."""
        self.template_line.duration = 20
        self.project_route.write({
            'duration': 20,
            'time_spent': 10
        })
        self.assertEqual(self.project_route.time_difference, 10, "Time difference is incorrect")

    def test_compute_on_hold(self):
        """Test the _compute_on_hold computed field."""
        self.project.address.on_hold = True
        route = self.project_route
        self.assertTrue(route.on_hold, "On hold should be True")

    def test_compute_act_name(self):
        self.template_line.acronym = 'TA'
        route = self.project_route
        # Force computation
        route._compute_act_name()
        self.assertIn("TA", route.act_work_order, "Work order should contain acronym")
        self.assertIn("Or", route.act_work_order, "Work order should contain county name")
        self.assertIn(str(route.id), route.act_work_order, "Work order should contain record id")

    def test_order_jobs(self):
        """Test the order_jobs method."""
        route = self.project_route
        route.order_jobs()
        self.assertIsNotNone(route.order_date, "Order date should be set")

    def test_complete_jobs(self):
        """Test the _complete_jobs method."""
        route = self.project_route
        route._complete_jobs()
        self.assertTrue(route.completed, "Job should be completed")
        self.assertEqual(route.pct_completed, 1.00, "Percent completed should be 100%")
        self.assertIsNotNone(route.end_date, "End date should be set")

    def test_uncomplete_jobs(self):
        """Test the uncomplete_jobs method."""
        route = self.project_route
        route.uncomplete_jobs()
        self.assertFalse(route.completed, "Job should be uncompleted")
        self.assertEqual(route.pct_completed, 0.00, "Percent completed should be 0%")
        self.assertFalse(route.end_date, "End date should be reset")

    def test_view_invoice(self):
        """Test the view_invoice method."""
        route = self.project_route
        with self.assertRaises(UserError):
            route.view_invoice()

        invoice = self.env['account.move'].create({'move_type': 'out_invoice'})
        route.invoice_id = invoice.id
        action = route.view_invoice()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'account.move')
        self.assertEqual(action['res_id'], invoice.id)
        self.assertEqual(action['view_mode'], 'form')
    
    def test_onchange_project_property(self):
        new_route_template = self.env['pms.projects.routes.templates'].create({'name': 'New Test Route Template'})
        new_template_line = self.env['pms.projects.routes.templates.lines'].create({
            'route_header': new_route_template.id,
            'name': 'New Test Activity',
            'sequence': 1,
            'phase': 'cop'
        })
        self.project.project_routes = new_route_template
        self.project.status_construction = 'cop1'

        route = self.env['pms.projects.routes'].new({'project_property': self.project.id})
        route._onchange_project_property()

        self.assertEqual(route.project_routes, new_route_template.id, "Project routes not updated")
        # self.assertEqual(route.name, new_template_line.id, "Activity name not updated")
        