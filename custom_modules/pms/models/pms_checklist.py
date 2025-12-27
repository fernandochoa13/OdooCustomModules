# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

# access_tmpl_mgr_checklist_tmpl,Project Checklist Template Manager,pms.model_project_checklist_template,pms.group_checklist_template_manager,1,1,1,1
# access_tmpl_mgr_checklist_tmpl_line,Project Checklist Template Line Manager,pms.model_project_checklist_template_line,pms.group_checklist_template_manager,1,1,1,1
# access_tmpl_mgr_checklist,Project Checklist Manager (Template Group),pms.model_project_checklist,pms.group_checklist_template_manager,1,1,1,1
# access_tmpl_mgr_checklist_line,Project Checklist Line Manager (Template Group),pms.model_project_checklist_line,pms.group_checklist_template_manager,1,1,1,1

# access_mgr_checklist,Project Checklist Manager,pms.model_project_checklist,pms.group_checklist_manager,1,1,1,1
# access_mgr_checklist_line,Project Checklist Line Manager,pms.model_project_checklist_line,pms.group_checklist_manager,1,1,1,1
# access_mgr_checklist_tmpl_read,Project Checklist Template Read/Write,pms.model_project_checklist_template,pms.group_checklist_manager,1,1,0,0
# access_mgr_checklist_tmpl_line_read,Project Checklist Template Line Read/Write,pms.model_project_checklist_template_line,pms.group_checklist_manager,1,1,0,0


class ProjectChecklistTemplate(models.Model):
    """
    Model for defining reusable project checklist templates.
    A template contains a set of standard checklist items that can be applied
    to multiple projects.
    """
    _name = 'project.checklist.template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Checklist Template'
    _order = 'name'

    name = fields.Char(string='Template Name', required=True, help="Name of this checklist template.")
    description = fields.Text(string='Description', help="A detailed description of what this template covers.")
    # One2many relationship to the template lines that define the checklist items
    template_line_ids = fields.One2many(
        'project.checklist.template.line', 
        'template_id', 
        string='Checklist Items',
        help="List of standard checklist items for this template."
    )
    active = fields.Boolean(
        string='Active', 
        default=True,
        help="If unchecked, the template will be hidden from most views."
    )

class ProjectChecklistTemplateLine(models.Model):
    """
    Model for individual checklist items within a checklist template.
    These are the generic tasks or confirmations.
    """
    _name = 'project.checklist.template.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Checklist Template Line'
    _order = 'sequence, name'

    name = fields.Char(string='Checklist Item', required=True, help="Description of the checklist item.")
    template_id = fields.Many2one(
        'project.checklist.template', 
        string='Checklist Template', 
        ondelete='cascade', 
        required=True,
        help="The template this item belongs to."
    )
    sequence = fields.Integer(string='Sequence', help="Order of the checklist item.")
    # Optional: Pre-assign a responsible user for this type of task
    # responsible_user_id = fields.Many2one(
    #     'res.users', 
    #     string='Default Responsible User',
    #     help="Default user responsible for this checklist item in new project checklists."
    # )
    # Link to project stages if items are relevant to specific phases.
    stage_id = fields.Many2one(
        'project.task.type', 
        string='Related Project Stage',
        help="If applicable, the project stage this checklist item relates to."
    )

class ProjectChecklist(models.Model):
    """
    Model for a specific checklist instance tied to a project.
    This is where field personnel will mark tasks as complete.
    """
    _name = 'project.checklist'
    _description = 'Project Checklist'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Checklist Reference', required=True, copy=False,
        default= _('New'),
        help="Unique reference for this project checklist.")
    
    # Reverted to specific Many2one to pms.project
    project_id = fields.Many2one(
        'pms.projects', 
        string='Project', # Updated string
        required=True, # Made required as it's the primary link
        tracking=True,
        help="The project this checklist is for."
    )

    template_id = fields.Many2one(
        'project.checklist.template', 
        string='Apply Template', 
        help="Select a template to automatically populate checklist items."
    )
    
    # One2many relationship to the individual checklist lines for this specific project checklist
    checklist_line_ids = fields.One2many(
        'project.checklist.line', 
        'checklist_id', 
        string='Checklist Tasks',
        copy=True,
        help="Individual tasks to be completed for this project checklist."
    )
    
    # user_id = fields.Many2one(
    #     'res.users', 
    #     string='Assigned To', 
    #     default=lambda self: self.env.user, 
    #     tracking=True,
    #     help="The user responsible for managing this checklist."
    # )
    # date_assigned = fields.Date(string='Assigned Date', default=fields.Date.today(), tracking=True, help="Date the checklist was assigned.")
    # date_completed = fields.Date(string='Completion Date', tracking=True, help="Date the checklist was marked as completed.")
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, help="Current status of the checklist.")
    
    progress = fields.Float(
        string='Progress (%)', 
        compute='_compute_progress', 
        store=True, 
        group_operator="avg",
        help="Percentage of completed checklist items."
    )

    @api.depends('checklist_line_ids.is_done')
    def _compute_progress(self):
        """
        Calculates the completion progress based on the number of 'is_done' lines.
        """
        for checklist in self:
            total_lines = len(checklist.checklist_line_ids)
            if total_lines:
                done_lines = len(checklist.checklist_line_ids.filtered(lambda l: l.is_done))
                checklist.progress = (done_lines / total_lines) * 100
            else:
                checklist.progress = 0.0

    @api.onchange('template_id')
    def _onchange_template_id(self):
        """
        When a template is selected, populate the checklist lines from the template lines.
        This will clear existing lines and add new ones from the chosen template.
        """
        if self.template_id:
            # Clear existing lines to avoid duplicates if template is changed
            self.checklist_line_ids = [(5, 0, 0)] 
            
            # Create new checklist lines from the template lines
            lines = []
            for t_line in self.template_id.template_line_ids:
                lines.append((0, 0, {
                    'name': t_line.name,
                    'sequence': t_line.sequence,
                    # 'responsible_user_id': t_line.responsible_user_id.id,
                    'stage_id': t_line.stage_id.id, 
                }))
            self.checklist_line_ids = lines



    def write(self, vals):
        """Override write to update completion date and state."""
        res = super(ProjectChecklist, self).write(vals)
        for rec in self:
            # Update state based on progress
            if rec.state == 'in_progress' and rec.progress == 100.0:
                rec.state = 'completed'
                rec.date_completed = fields.Date.today()
            elif rec.state == 'completed' and rec.progress < 100.0:
                rec.state = 'in_progress'
                rec.date_completed = False
            elif not rec.checklist_line_ids and rec.state not in ('draft', 'cancelled'):
                rec.state = 'draft' # Reset to draft if all lines are removed
        return res

class ProjectChecklistLine(models.Model):
    """
    Model for an individual task within a specific project checklist.
    This is where the boolean confirmation happens.
    """
    _name = 'project.checklist.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Project Checklist Line'
    _order = 'sequence, name'

    name = fields.Char(string='Task Description', required=True, default=_('New Checklist Item'), help="Description of the task to be confirmed.")
    checklist_id = fields.Many2one(
        'project.checklist', 
        string='Project Checklist',
        ondelete='cascade', 
        required=True,
        help="The project checklist this task belongs to."
    )
    is_done = fields.Boolean(string='Done', help="Mark this task as completed.")
    # completed_by_id = fields.Many2one(
    #     'res.users', 
    #     string='Completed By', 
    #     help="The user who marked this task as done."
    # )
    completion_date = fields.Datetime(string='Completion Timestamp', help="When the task was marked as done.")
    # responsible_user_id = fields.Many2one(
    #     'res.users', 
    #     string='Responsible User',
    #     help="The specific user assigned to complete this task."
    # )
    notes = fields.Text(string='Notes', help="Any additional notes or comments regarding this task.")
    sequence = fields.Integer(string='Sequence', default=10, help="Order of the task within the checklist.")
    stage_id = fields.Many2one(
        'project.task.type', 
        string='Related Project Stage',
        help="If applicable, the project stage this checklist item relates to (inherited from template or set manually)."
    )

    # is_admin = fields.Boolean(
    #     string='Is Admin User',
    #     compute='_compute_is_admin_user',
    #     help="Technical field: True if the current user belongs to the 'Administrator' group."
    # )

    # @api.depends_context('uid') 
    # def _compute_is_admin_user(self):
    #     """
    #     Determines if the current user is an administrator.
    #     """
    #     for record in self:
    #         record.is_admin = self.env.user.has_group('base.group_system')

    @api.onchange('is_done')
    def _onchange_is_done(self):
        """
        Updates completion details when the 'is_done' field changes.
        """
        if self.is_done:
            # self.completed_by_id = self.env.user
            self.completion_date = datetime.now()
        else:
            # self.completed_by_id = False
            self.completion_date = False