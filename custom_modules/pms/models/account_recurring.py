from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta



class account_recurring(models.Model):
    _name = "account.recurring"
    _description = "Account Recurring"

    name = fields.Char(required=True, string="Name of Recurring")
    model_journal = fields.Many2one("account.move", string="Journal")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    posted_moves = fields.One2many("account.move", "recurring_id", string="Recurring ID", readonly=True)
    state = fields.Selection([("draft", "Draft"), ("running", "Running"), ("stop", "Stopped")], string="State", default="draft", readonly=True)
    company = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    period = fields.Selection([("daily", "Daily"), ("weekly", "Weekly"), ("monthly", "Monthly")], string="Period")
    period_count = fields.Integer(string="Every x Period")
    next_date = fields.Date(string="Next Date", readonly=True)

    def action_start(self):
        for record in self:
            record.state = "running"
            if record.next_date == False:
                record.next_date = record.start_date

    def action_stop(self):
        for record in self:
            record.state = "stop"


    def _post_moves(self):
        # Get List of Moves that have next date less than or equal to today
        today = fields.Date.today()
        moves = self.env["account.recurring"].search(["&", ("state", "=", "running"), "|", ("next_date", "=", today), ("next_date", "<=", today)])
        
        for move in moves:
            
            # Create a new move
            new_move = move.model_journal.copy()
            
            new_move.recurring_id = move.id
            new_move.date = today
            new_move.state = "draft"
            move.posted_moves = [(4, new_move.id)]
            move._get_next_date()
            move.posted_moves = [(4, new_move.id)]

    def post_next_moves(self):
        # Get List of Moves that have next date less than or equal to today
        # today = fields.Date.today()
        # moves = self.env["account.recurring"].search(["&", ("state", "=", "running"), "|", ("next_date", "=", today), ("next_date", "<=", today)])
        
        for record in self:
            if record.state == "running":
                new_move = record.model_journal.copy()
                new_move.recurring_id = record.id
                new_move.date = record.next_date
                new_move.state = "posted"
                record.posted_moves = [(4, new_move.id)]
                record._get_same_next_date()
                record.posted_moves = [(4, new_move.id)]
            else:
                return False

    def _get_next_date(self):
        # Get the next date based on the period and period count
        self.ensure_one()

        today = fields.Date.today()

        # Checking for end_date
        if self.end_date <= today:
            self.action_stop()
            return False

        if self.period == "daily":
            self.next_date = today + timedelta(days=self.period_count)
            
        elif self.period == "weekly":
            self.next_date = today + timedelta(weeks=self.period_count)
            
        elif self.period == "monthly":
            self.next_date = today + relativedelta(months=self.period_count)

        else:
            self.action_stop()

    def _get_same_next_date(self):
        self.ensure_one()

        today = self.next_date

        if self.end_date <= today:
            self.action_stop()
            return False

        if self.period == "daily":
            self.next_date = today + timedelta(days=self.period_count)
            
        elif self.period == "weekly":
            self.next_date = today + timedelta(weeks=self.period_count)
            
        elif self.period == "monthly":
            self.next_date = today + relativedelta(months=self.period_count)

        else:
            self.action_stop()
        
    
    def get_posted_entries_view(self):
        return {
            "name": "Posted Entries",
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.posted_moves.ids)]
        }