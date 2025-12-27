from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class CreateMOWizard(models.TransientModel):
    _name = 'material.orders.wizard'
    _description = 'Create Material Orders Wizard'

    def create_material_order(self):
        invoice_line_ids = self.env.context.get('default_invoice_line_ids')
        # estimated_delivery_date = self.env.context.get('default_date_receipted')
        provider = self.env.context.get('default_partner_id')
        bill_id = self.env.context.get('default_bill_id')
        invoice_date = self.env.context.get('default_invoice_date')

        duplicates = self.env["pms.materials"].search([("bill_id", "=", bill_id)])
        if duplicates:
            raise ValidationError("Material orders already exist for this bill.")

        lines = self.env['account.move.line'].browse(invoice_line_ids)

        grouped_lines = {}
        for line in lines:
            analytic_distribution = line.analytic_distribution
            if not analytic_distribution:
                raise ValidationError("Analytic distribution not found for this line.")
            
            analytic_account_id = int(list(analytic_distribution.keys())[0])

            if analytic_account_id not in grouped_lines:
                grouped_lines[analytic_account_id] = []
            
            grouped_lines[analytic_account_id].append(line)

        for analytic_account_id, lines_group in grouped_lines.items():
            order_lines = []
            for line in lines_group:
                order_lines.append((0, 0, {
                    'product': line.product_id.id,
                    'subproduct': line.subproducts.id,
                    'quantity': line.quantity,
                    'amount': line.price_unit
                }))

            property_record = self.env['pms.property'].search([('analytical_account', '=', analytic_account_id)], limit=1)

            if property_record:
                material_order = {
                    "property_id": property_record.id,
                    "estimated_delivery_date": invoice_date,
                    "material_lines": order_lines,
                    "provider": provider,
                    "bill_id": bill_id,
                    "has_bill": True,
                }

                self.env["pms.materials"].create(material_order)
            else:
                raise ValidationError(f"No property found for analytic account ID {analytic_account_id}.")





