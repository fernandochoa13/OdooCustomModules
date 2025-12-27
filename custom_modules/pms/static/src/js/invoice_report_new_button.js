/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class InvoiceReportListController extends ListController {
    setup() {
        super.setup();
    }

    OnCreateInvoice() {
        this.actionService.doAction({
            name: 'Create Invoice',
            type: 'ir.actions.act_window',
            res_model: 'account.move',
            views: [[false, 'form']],
            target: 'current', 
            context: {
                'default_move_type': 'out_invoice', 
            },
        })
    }
}

registry.category("views").add("button_in_invoice_report_tree", {
    ...listView,
    Controller: InvoiceReportListController,
    buttonTemplate: "button_invoice_report.ListView.Buttons",
});