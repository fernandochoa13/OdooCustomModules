from odoo import models, fields, _, api

import logging
_logger = logging.getLogger(__name__)

class property_timeline_report(models.Model):
    _name = "pms.property.timeline.report"
    _description = "Property Timeline Report"
    _auto = False

    # query of the gantt determined in wizard
    property_id = fields.Many2one("pms.property", string="Property", readonly=True)
    
    # Default group by of the gantt
    status = fields.Selection(string="Status", readonly=True, selection=[
        ("pending", "Pending"), ("pip", "PIP"), ("pps", "PPS"), ("epp", "EPP"), 
        ("pip", "PIP"), ("pps", "PPS"), ("ppa", "PPA"), ("cop", "COP"), ("cop1", "COP1"), 
        ("cop2", "COP2"), ("cop3", "COP3"), ("cop4", "COP4"), ("cop5", "COP5"), ("coc", "COC"), ("completed", "Completed"), ("no_phase", "No Phase")
        ])
    
    # Will determine the color of the gantt item
    type = fields.Selection(string="Type of Record", readonly=True, selection=[
        ("on_hold", "On Hold"), # query a on_hold_history
        ("activity", "Activity"), # query on pms_projects
        ('inspection_passed', 'Inspection Passed'),
        ('inspection_passed_after', 'Inspection Passed After Reinspection'),
        ('inspection_ordered', 'Inspection Ordered'),
        ('inspection_failed', 'Inspection Failed'),
        ("invoice", "Invoice") # query on account_move, must assign status based on the closest record in the table to its record_start_date
    ])
    color = fields.Integer(string="Color", compute='_compute_color', default=0)  # Or fields.Selection

    @api.depends('type')
    def _compute_color(self):
        for rec in self:
            if rec.type == 'on_hold':
                rec.color = 1 # red
            elif rec.type == 'activity':
                rec.color = 4 # blue
            elif rec.type == 'invoice':
                rec.color = 5 # Purple
            elif rec.type == "inspection_passed":
                rec.color = 10 # green
            elif rec.type == "inspection_passed_after":
                rec.color = 3 # yellow
            elif rec.type == "inspection_ordered":
                rec.color = 0 # gray
            elif rec.type == "inspection_failed":
                rec.color = 2 # Orange 

    # Will be the label of the gantt item
    name = fields.Char(string="Record Name", readonly=True)
    
    # Starting and Ending dates for the gantt item
    record_start_date = fields.Date(string="Start Date", readonly=True)
    record_end_date = fields.Date(string="End Date", readonly=True)
    
    
    # projects_activities, property, account_move on_hold_history 
    
    # Step 1: seleccionas propiedad y busca la propiedad que se selecciona
    # va a agrupar por status_construction
    # if end_date is null put a future date to simbolize its not done
    
    # Error fields
    

    @property
    def _table_query(self):
        property_id = self.env.context.get('property_id')
        _logger.info("Selected property: " + str(property_id))
        
        return f"""
    
                -- ON HOLD QUERY
                
                SELECT
                
                    ohh.id AS id,
                    ohh.date AS record_start_date,
                    COALESCE(ohh.hold_end_date, DATE('9999-12-31')) AS record_end_date,
                    CASE
                        WHEN ohh.off_hold_reason IS NOT NULL AND ohh.comments IS NOT NULL THEN 'On Hold: ' || INITCAP(ohh.off_hold_reason) || ' - ' || ohh.comments
                        WHEN ohh.off_hold_reason IS NOT NULL THEN 'On Hold: ' || INITCAP(ohh.off_hold_reason)
                        WHEN ohh.comments IS NOT NULL THEN 'On Hold: ' || INITCAP(ohh.comments)
                        ELSE 'On Hold: No reason provided'
                    END AS name,
                    'on_hold' AS type,
                    ohh.previous_status AS status,
                    {property_id} AS property_id
                    
                FROM pms_on_hold_history AS ohh
                WHERE ohh.property_name = {property_id}

                UNION ALL
                
                -- ACTIVITY QUERY

                SELECT
                
                    ppr.id AS id,
                    ppr.order_date AS record_start_date,
                    COALESCE(ppr.end_date, DATE('9999-12-31')) AS record_end_date,
                    'Activity: ' || prtl.name AS name,
                    'activity' AS type,
                    prtl.phase AS status,
                    {property_id} AS property_id
                    
                    
                FROM pms_projects_routes AS ppr
                INNER JOIN pms_projects AS pp ON ppr.project_property = pp.id
                INNER JOIN pms_projects_routes_templates_lines AS prtl ON ppr.name = prtl.id
                WHERE pp.address = {property_id}
                
                UNION ALL
                
                -- INSPECTION QUERY
                
                SELECT
                    pi.id AS id,
                    pi.date AS record_start_date,
                    CASE
                        WHEN pi.status IN ('ordered', 'failed') THEN DATE('9999-12-31')
                        WHEN pi.status IN ('passed', 'passed_after') THEN COALESCE(pi.end_date, pi.date)
                    END AS record_end_date,
                    CASE
                        WHEN pi.status = 'passed' THEN 'Inspection Passed: ' || pi.name
                        WHEN pi.status = 'passed_after' THEN 'Inspection Passed After Re-Inspection: ' || pi.name
                        WHEN pi.status = 'ordered' THEN 'Inspection Ordered: ' || pi.name
                        WHEN pi.status = 'failed' THEN 'Inspection Failed: ' || pi.name
                    END AS name,
                    CASE
                        WHEN pi.status = 'passed' THEN 'inspection_passed'
                        WHEN pi.status = 'passed_after' THEN 'inspection_passed_after'
                        WHEN pi.status = 'ordered' THEN 'inspection_ordered'
                        WHEN pi.status = 'failed' THEN 'inspection_failed'
                    END AS type,
                    COALESCE(pi.construction_status, 'pps') AS status,
                    {property_id} AS property_id
                    
                
                FROM pms_inspections pi
                WHERE pi.address = {property_id}
                
                UNION ALL
                
                -- INVOICE QUERY

                SELECT
                    (ARRAY_AGG(aml.id))[1] AS id,
                    am.date AS record_start_date,
                    COALESCE(sub2.date, DATE('9999-12-31')) AS record_end_date,
                    'Invoice: ' || am.payment_reference || ' (' || am.name || ')' AS name,
                    'invoice' AS type,
                    COALESCE(
                        (
                            SELECT prtl.phase
                            FROM pms_projects_routes AS ppr
                            INNER JOIN pms_projects AS pp2 ON ppr.project_property = pp2.id
                            INNER JOIN pms_projects_routes_templates_lines AS prtl ON ppr.name = prtl.id
                            WHERE pp2.address = {property_id}
                            AND am.date BETWEEN 
                                ppr.order_date - interval '15 days' 
                                AND COALESCE(ppr.end_date, DATE('9999-12-31')) + interval '15 days'

                            LIMIT 1
                        ),
                        'no_phase'
                    ) AS status,
                    {property_id} AS property_id
                FROM account_analytic_line AS aal
                INNER JOIN pms_property AS pp ON aal.account_id = pp.analytical_account
                INNER JOIN account_move_line AS aml ON aal.move_line_id = aml.id
                INNER JOIN account_move AS am ON aml.move_id = am.id
                INNER JOIN account_payment_term AS apt ON am.invoice_payment_term_id = apt.id
                LEFT JOIN account_account AS aa ON aml.account_id = aa.id AND aa.account_type = 'asset_receivable'
                INNER JOIN 
                (
                    SELECT 
                        (ARRAY_AGG(am2.id))[1] AS id,
                        aml2.matching_number AS matching_number
                    FROM account_move AS am2
                    INNER JOIN account_move_line AS aml2 ON am2.id = aml2.move_id
                    WHERE am2.move_type = 'out_invoice'
                    AND matching_number IS NOT NULL
                    AND aml2.credit = 0
                    GROUP BY aml2.matching_number
                ) sub1 ON am.id = sub1.id
                LEFT JOIN 
                (
                    SELECT 
                        aml3.date AS date,
                        aml3.matching_number AS matching_number
                    FROM account_move_line AS aml3
                    WHERE aml3.matching_number IS NOT NULL
                    AND aml3.debit = 0
                ) sub2 ON sub1.matching_number = sub2.matching_number
                WHERE am.move_type = 'out_invoice'
                AND (apt.utility_payment OR apt.material_payment)
                AND pp.id = {property_id}
                GROUP BY am.date, am.name, sub2.date, am.payment_reference
            """
            
            
                # LEFT JOIN account_move_line AS aml_clearing ON aml.matching_number = aml_clearing.matching_number
                #     AND aml_clearing.account_id IN 
                #     (
                #         SELECT id 
                #         FROM account_account 
                #         WHERE account_type = 'asset_receivable'
                #     )
                #     AND aml_clearing.credit = 0
            
            # (
            #     SELECT pi.construction_status
            #     FROM pms_inspections pi
            #     WHERE pi.address = {property_id}
            #     AND am.date BETWEEN pi.date AND COALESCE(pi.end_date, DATE('9999-12-31'))
            #     LIMIT 1
            # ),
            
                # UNION ALL
            
                # SELECT
                
                #     am.id AS id,
                #     am.date AS record_start_date,
                #     CASE
                #         WHEN am.payment_status IN ('not_paid', 'partial') THEN DATE('9999-12-31')
                #         WHEN aml.account_type = "asset_receivable" THEN (
                #             SELECT

                #             FROM account_account aa
                #         )
                #     END AS record_end_date,
                #     'Invoice delay: ' || ? AS name,
                #     ? AS status,
                #     'invoice' AS type
                    
                    
                # FROM account_analytic_line AS aal
                # INNER JOIN account_move_line AS aml ON aal.move_line_id = aml.id
                # INNER JOIN account_move AS am ON aml.move_id = am.id
                # INNER JOIN account_payment_term AS apt ON am.invoice_payment_term_id = apt.id
                # INNER JOIN pms_property pp AS pp ON aal.account_id = pp.analytical_account
                
                
                # WHERE pp.id = {property_id}
                # AND apt.material_payment = true
                # AND am.move_type = 'out_invoice'
                
                
# Cuando el invoice este pagado hay q buscar en account move line que la cuenta la cual tiene una relacion 
# con account_account tenga el tipo de receivable en esa linea checkea el campo full_reconcile_id y hazle 
# un join con la tabla account_full_reconcile y esa tabla account_full_reconcile tiene un campo llamado 
# exchange_move_id ver ese campo en account_move y retornar su date
# quizas no sea el campo exchange_move_id sino reconciled_line_ids el cual es un one2many y por ende hay 
# q hacer un join para buscar todos los asientos en account move line con ese id de account full reconcile 
# y con ese id agarrar el line q tenga la cuenta de account receivable osea de tipo receivable con un monto 
# mayor a 0 en el haber y agarra la fecha de ese registro como la fecha de pago
            

            
            

    
class timeline_select_property_wizard(models.TransientModel):
    _name = 'timeline.select.property.wizard'
    _description = 'Timeline Select Property Wizard'
    
    property_id = fields.Many2one('pms.property', string='Property', required=True)
    
    def select_property(self):
        
        form_view = self.env.ref('pms.pms_property_timeline_view_report_gantt')
        
        if self.property_id:
            return {
                'name': 'Property Timeline Report',
                'type': 'ir.actions.act_window',
                'res_model': 'pms.property.timeline.report',
                'view_mode': 'gantt',
                'view_id': form_view.id,
                'target': 'current',
                'context': {'property_id': self.property_id.id}
            }
    