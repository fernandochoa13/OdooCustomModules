/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class InvoiceReportListController extends ListController {
    setup() {
        super.setup();
    }

    OnChangeLoanReport() {
        this.actionService.doAction({
            name: 'New Loan Report',
            type: 'ir.actions.act_window',
            res_model: 'select.property.loan.report.wizard',
            views: [[false, 'form']],
            target: 'new', 
        })
    }
}

registry.category("views").add("button_in_property_loan_report_tree", {
    ...listView,
    Controller: InvoiceReportListController,
    buttonTemplate: "button_property_loan_report.ListView.Buttons",
});