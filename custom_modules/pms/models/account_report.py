# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api
from psycopg2 import sql
from ast import literal_eval
from collections import defaultdict
from odoo.exceptions import RedirectWarning, UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class AccountReport(models.Model):
    _inherit = 'account.report'
    def _compute_formula_batch_with_engine_domain(self, options, date_scope, formulas_dict, current_groupby, next_groupby, offset=0, limit=None):
        """ Report engine.

        Formulas made for this engine consist of a domain on account.move.line. Only those move lines will be used to compute the result.

        This engine supports a few subformulas, each returning a slighlty different result:
        - sum: the result will be sum of the matched move lines' balances

        - sum_if_pos: the result will be the same as sum only if it's positive; else, it will be 0

        - sum_if_neg: the result will be the same as sum only if it's negative; else, it will be 0

        - count_rows: the result will be the number of sublines this expression has. If the parent report line has no groupby,
                        then it will be the number of matching amls. If there is a groupby, it will be the number of distinct grouping
                        keys at the first level of this groupby (so, if groupby is 'partner_id, account_id', the number of partners).
        """
        def _format_result_depending_on_groupby(formula_rslt):
            if not current_groupby:
                if formula_rslt:
                    # There should be only one element in the list; we only return its totals (a dict) ; so that a list is only returned in case
                    # of a groupby being unfolded.
                    return formula_rslt[0][1]
                else:
                    # No result at all
                    return {
                        'sum': 0,
                        'sum_if_pos': 0,
                        'sum_if_neg': 0,
                        'count_rows': 0,
                        'has_sublines': False,
                    }
            return formula_rslt

        self._check_groupby_fields((next_groupby.split(',') if next_groupby else []) + ([current_groupby] if current_groupby else []))

        groupby_sql = f'account_move_line.{current_groupby}' if current_groupby else None
        ct_query = self.env['res.currency']._get_query_currency_table(options)

        rslt = {}

        for formula, expressions in formulas_dict.items():
            try:
                line_domain = literal_eval(formula)
            except (ValueError, SyntaxError):
                raise UserError(_("Invalid domain formula in expression %r of line %r: %s", expressions.label, expressions.report_line_id.name, formula))
            tables, where_clause, where_params = self._query_get(options, date_scope, domain=line_domain)

            tail_query, tail_params = self._get_engine_query_tail(offset, limit)
            query = f"""
                SELECT
                    COALESCE(SUM(ROUND(account_move_line.balance * currency_table.rate, 6)), 0.0) AS sum,
                    COUNT(DISTINCT account_move_line.{next_groupby.split(',')[0] if next_groupby else 'id'}) AS count_rows
                    {f', {groupby_sql} AS grouping_key' if groupby_sql else ''}
                FROM {tables}
                JOIN {ct_query} ON currency_table.company_id = account_move_line.company_id
                WHERE {where_clause}
                {f' GROUP BY {groupby_sql}' if groupby_sql else ''}
                {tail_query}
            """

            # Fetch the results.
            formula_rslt = []
            self._cr.execute(query, where_params + tail_params)
            all_query_res = self._cr.dictfetchall()

            total_sum = 0
            for query_res in all_query_res:
                res_sum = query_res['sum']
                total_sum += res_sum
                totals = {
                    'sum': res_sum,
                    'sum_if_pos': 0,
                    'sum_if_neg': 0,
                    'count_rows': query_res['count_rows'],
                    'has_sublines': query_res['count_rows'] > 0,
                }
                formula_rslt.append((query_res.get('grouping_key', None), totals))

            # Handle sum_if_pos, -sum_if_pos, sum_if_neg and -sum_if_neg
            expressions_by_sign_policy = defaultdict(lambda: self.env['account.report.expression'])
            for expression in expressions:
                subformula_without_sign = expression.subformula.replace('-', '').strip()
                if subformula_without_sign in ('sum_if_pos', 'sum_if_neg'):
                    expressions_by_sign_policy[subformula_without_sign] += expression
                else:
                    expressions_by_sign_policy['no_sign_check'] += expression

            # Then we have to check the total of the line and only give results if its sign matches the desired policy.
            # This is important for groupby managements, for which we can't just check the sign query_res by query_res
            if expressions_by_sign_policy['sum_if_pos'] or expressions_by_sign_policy['sum_if_neg']:
                sign_policy_with_value = 'sum_if_pos' if self.env.company.currency_id.compare_amounts(total_sum, 0.0) >= 0 else 'sum_if_neg'
                # >= instead of > is intended; usability decision: 0 is considered positive

                formula_rslt_with_sign = [(grouping_key, {**totals, sign_policy_with_value: totals['sum']}) for grouping_key, totals in formula_rslt]

                for sign_policy in ('sum_if_pos', 'sum_if_neg'):
                    policy_expressions = expressions_by_sign_policy[sign_policy]

                    if policy_expressions:
                        if sign_policy == sign_policy_with_value:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby(formula_rslt_with_sign)
                        else:
                            rslt[(formula, policy_expressions)] = _format_result_depending_on_groupby([])

            if expressions_by_sign_policy['no_sign_check']:
                rslt[(formula, expressions_by_sign_policy['no_sign_check'])] = _format_result_depending_on_groupby(formula_rslt)

        return rslt


    @api.model
    def _cleanup_cash_basis_data(self):
        self.env.cr.execute("""
           DROP TABLE IF EXISTS cash_basis_temp_account_move_line;
           DROP TABLE IF EXISTS analytic_cash_basis_temp_account_move_line;
           DROP TABLE IF EXISTS analytic_temp_account_move_line;
        """)
        self._prepare_lines_for_cash_basis()
        self._prepare_lines_for_analytic_groupby_with_cash_basis()
        self._prepare_lines_for_analytic_groupby()

    @api.model
    def _delete_cash_basis_entries_for_moves(self, move_ids):
        """Deletes entries from the temp table for a specific list of moves."""
        if not move_ids:
            return
        self.env.cr.execute("DELETE FROM cash_basis_temp_account_move_line WHERE move_id IN %s", [tuple(move_ids)])

    @api.model
    def _insert_cash_basis_entries_for_moves(self, move_ids, state):
        """Calculates and inserts cash basis entries for a specific list of moves."""
        if not move_ids:
            return

        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        changed_fields = ['date', 'amount_currency', 'amount_residual', 'balance', 'debit', 'credit', 'parent_state']
        unchanged_fields = list(set(f[0] for f in self.env.cr.fetchall()) - set(changed_fields))
        if len(move_ids) == 1:
            move_ids = f"({move_ids[0]})"
        else:
            move_ids = tuple(move_ids)

        if state == False:
            state = '"account_move_line".parent_state'
        sql = """
            INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                {unchanged_fields},
                "account_move_line".date,
                "account_move_line".amount_currency,
                "account_move_line".amount_residual,
                "account_move_line".balance,
                "account_move_line".debit,
                "account_move_line".credit,
                {state}
            FROM ONLY account_move_line
            WHERE account_move_line.move_id IN {move_ids} AND (
                "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                OR "account_move_line".move_id NOT IN (
                    SELECT DISTINCT aml.move_id
                    FROM ONLY account_move_line aml
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
            );

            WITH payment_table AS (
                SELECT
                    aml.move_id,
                    GREATEST(aml.date, aml2.date) AS date,
                    CASE WHEN (aml.balance = 0 OR sub_aml.total_per_account = 0)
                        THEN 0
                        ELSE round(part.amount / ABS(sub_aml.total_per_account), 4)
                    END as matched_percentage
                FROM account_partial_reconcile part
                JOIN ONLY account_move_line aml ON aml.id = part.debit_move_id OR aml.id = part.credit_move_id
                JOIN ONLY account_move_line aml2 ON
                    (aml2.id = part.credit_move_id OR aml2.id = part.debit_move_id)
                    AND aml.id != aml2.id
                JOIN (
                    SELECT move_id, account_id, SUM(ABS(balance)) AS total_per_account
                    FROM ONLY account_move_line account_move_line
                    GROUP BY move_id, account_id
                ) sub_aml ON (aml.account_id = sub_aml.account_id AND aml.move_id=sub_aml.move_id)
                JOIN account_account account ON aml.account_id = account.id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                AND aml.move_id IN {move_ids}
            )
            INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                {unchanged_fields},
                ref.date,
                round(ref.matched_percentage * "account_move_line".amount_currency, 4),
                round(ref.matched_percentage * "account_move_line".amount_residual, 4),
                round(ref.matched_percentage * "account_move_line".balance, 4),
                round(ref.matched_percentage * "account_move_line".debit, 4),
                round(ref.matched_percentage * "account_move_line".credit, 4),
                {state}
            FROM payment_table ref
            JOIN ONLY account_move_line account_move_line ON "account_move_line".move_id = ref.move_id
            WHERE account_move_line.move_id IN {move_ids} AND NOT (
                "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                OR "account_move_line".move_id NOT IN (
                    SELECT DISTINCT aml.move_id
                    FROM ONLY account_move_line aml
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
            )
            ;
        """.format(
            all_fields=', '.join(f'"{f}"' for f in (unchanged_fields + changed_fields)),
            unchanged_fields=', '.join([f'"account_move_line"."{f}"' for f in unchanged_fields]),
            move_ids=move_ids,
            state=state
        )
        _logger.info(sql)
        self.env.cr.execute(sql)
        
    @api.model
    def _update_cash_basis_entries_for_moves(self, move_ids, state):
        """Atomically updates cash basis entries by deleting old ones and inserting new ones."""
        _logger.info("runngin update cash")
        if not move_ids:
            return
        # By putting these in the same job, they run in the same transaction.
        self._delete_cash_basis_entries_for_moves(move_ids)
        self._insert_cash_basis_entries_for_moves(move_ids, state)


    @api.model
    def _prepare_lines_for_cash_basis(self):
        """Prepare the cash_basis_temp_account_move_line substitue.

        This method should be used once before all the SQL queries using the
        table account_move_line for reports in cash basis.
        It will create a new table like the account_move_line table, but with
        amounts and the date relative to the cash basis.
        """
        self.env.cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name='cash_basis_temp_account_move_line'")
        if self.env.cr.fetchone():
            return

        # TODO gawa Analytic + CABA, check the shadowing
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        changed_fields = ['date', 'amount_currency', 'amount_residual', 'balance', 'debit', 'credit']
        unchanged_fields = list(set(f[0] for f in self.env.cr.fetchall()) - set(changed_fields))
        selected_journals = tuple(self.env.context.get('journal_ids', []))
        sql = """   -- Create a temporary table
            CREATE TABLE IF NOT EXISTS cash_basis_temp_account_move_line AS TABLE account_move_line WITH NO DATA;

            INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                {unchanged_fields},
                "account_move_line".date,
                "account_move_line".amount_currency,
                "account_move_line".amount_residual,
                "account_move_line".balance,
                "account_move_line".debit,
                "account_move_line".credit
            FROM ONLY account_move_line
            WHERE (
                "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                OR "account_move_line".move_id NOT IN (
                    SELECT DISTINCT aml.move_id
                    FROM ONLY account_move_line aml
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
            )
            {where_journals};

            WITH payment_table AS (
                SELECT
                    aml.move_id,
                    GREATEST(aml.date, aml2.date) AS date,
                    CASE WHEN (aml.balance = 0 OR sub_aml.total_per_account = 0)
                        THEN 0
                        ELSE part.amount / ABS(sub_aml.total_per_account)
                    END as matched_percentage
                FROM account_partial_reconcile part
                JOIN ONLY account_move_line aml ON aml.id = part.debit_move_id OR aml.id = part.credit_move_id
                JOIN ONLY account_move_line aml2 ON
                    (aml2.id = part.credit_move_id OR aml2.id = part.debit_move_id)
                    AND aml.id != aml2.id
                JOIN (
                    SELECT move_id, account_id, SUM(ABS(balance)) AS total_per_account
                    FROM ONLY account_move_line account_move_line
                    GROUP BY move_id, account_id
                ) sub_aml ON (aml.account_id = sub_aml.account_id AND aml.move_id=sub_aml.move_id)
                JOIN account_account account ON aml.account_id = account.id
                WHERE account.account_type IN ('asset_receivable', 'liability_payable')
            )
            INSERT INTO cash_basis_temp_account_move_line ({all_fields}) SELECT
                {unchanged_fields},
                ref.date,
                ref.matched_percentage * "account_move_line".amount_currency,
                ref.matched_percentage * "account_move_line".amount_residual,
                ref.matched_percentage * "account_move_line".balance,
                ref.matched_percentage * "account_move_line".debit,
                ref.matched_percentage * "account_move_line".credit
            FROM payment_table ref
            JOIN ONLY account_move_line account_move_line ON "account_move_line".move_id = ref.move_id
            WHERE NOT (
                "account_move_line".journal_id IN (SELECT id FROM account_journal WHERE type in ('cash', 'bank'))
                OR "account_move_line".move_id NOT IN (
                    SELECT DISTINCT aml.move_id
                    FROM ONLY account_move_line aml
                    JOIN account_account account ON aml.account_id = account.id
                    WHERE account.account_type IN ('asset_receivable', 'liability_payable')
                )
            )
            {where_journals};
            CREATE INDEX ON cash_basis_temp_account_move_line (date);
            CREATE INDEX ON cash_basis_temp_account_move_line (parent_state);
            CREATE INDEX ON cash_basis_temp_account_move_line (account_id);
            CREATE INDEX ON cash_basis_temp_account_move_line (company_id);
            ;
        """.format(
            all_fields=', '.join(f'"{f}"' for f in (unchanged_fields + changed_fields)),
            unchanged_fields=', '.join([f'"account_move_line"."{f}"' for f in unchanged_fields]),
            where_journals=selected_journals and 'AND "account_move_line".journal_id IN %(journal_ids)s' or ''
        )
        params = {
            'journal_ids': selected_journals,
        }
        self.env.cr.execute(sql, params)


    @api.model
    def _prepare_lines_for_analytic_groupby(self):
        """Prepare the analytic_temp_account_move_line

        This method should be used once before all the SQL queries using the
        table account_move_line for the analytic columns for the financial reports.
        It will create a new table with the schema of account_move_line table, but with
        the data from account_analytic_line.

        We inherit the schema of account_move_line, make the correspondence between
        account_move_line fields and account_analytic_line fields and put NULL for those
        who don't exist in account_analytic_line.
        We also drop the NOT NULL constraints for fields who are not required in account_analytic_line.
        """
        self.env.cr.execute(
            "SELECT 1 FROM information_schema.tables WHERE table_name='analytic_temp_account_move_line'")
        if self.env.cr.fetchone():
            return

        line_fields = self.env['account.move.line'].fields_get()
        self.env.cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_move_line'")
        stored_fields = set(f[0] for f in self.env.cr.fetchall())
        changed_equivalence_dict = {
            "id": sql.Identifier("id"),
            "balance": sql.SQL("-amount"),
            "company_id": sql.Identifier("company_id"),
            "journal_id": sql.Identifier("journal_id"),
            "display_type": sql.Literal("product"),
            "parent_state": sql.Literal("posted"),
            "date": sql.Identifier("date"),
            "account_id": sql.Identifier("general_account_id"),
            "partner_id": sql.Identifier("partner_id"),
            "debit": sql.SQL("CASE WHEN (amount < 0) THEN amount else 0 END"),
            "credit": sql.SQL("CASE WHEN (amount > 0) THEN amount else 0 END"),
        }
        selected_fields = []
        for fname in stored_fields:
            if fname in changed_equivalence_dict:
                selected_fields.append(sql.SQL('{original} AS "account_move_line.{asname}"').format(
                    original=changed_equivalence_dict[fname],
                    asname=sql.SQL(fname),
                ))
            elif fname == 'analytic_distribution':
                selected_fields.append(sql.SQL('to_jsonb(account_id) AS "account_move_line.analytic_distribution"'))
            else:
                if line_fields[fname].get("translate"):
                    typecast = sql.SQL('jsonb')
                elif line_fields[fname].get("type") in ("many2one", "one2many", "many2many", "monetary"):
                    typecast = sql.SQL('integer')
                elif line_fields[fname].get("type") == "datetime":
                    typecast = sql.SQL('date')
                elif line_fields[fname].get("type") == "selection":
                    typecast = sql.SQL('text')
                else:
                    typecast = sql.SQL(line_fields[fname].get("type"))
                selected_fields.append(sql.SQL('cast(NULL AS {typecast}) AS "account_move_line.{fname}"').format(
                    typecast=typecast,
                    fname=sql.SQL(fname),
                ))

        query = sql.SQL("""
            -- Create a temporary table, dropping not null constraints because we're not filling those columns
            CREATE TABLE IF NOT EXISTS analytic_temp_account_move_line AS TABLE account_move_line WITH NO DATA;
            ALTER TABLE analytic_temp_account_move_line ALTER COLUMN move_id DROP NOT NULL;
            ALTER TABLE analytic_temp_account_move_line ALTER COLUMN currency_id DROP NOT NULL;

            INSERT INTO analytic_temp_account_move_line ({all_fields})
            SELECT {table}
            FROM (SELECT * FROM account_analytic_line WHERE general_account_id IS NOT NULL) AS account_analytic_line;

            CREATE INDEX IF NOT EXISTS analytic_temp_account_move_line__composite_idx ON analytic_temp_account_move_line (analytic_distribution, journal_id, date, company_id);
            ANALYZE analytic_temp_account_move_line
        """).format(
            all_fields=sql.SQL(', ').join(sql.Identifier(fname) for fname in stored_fields),
            table=sql.SQL(', ').join(selected_fields),
        )

        self.env.cr.execute(query)
