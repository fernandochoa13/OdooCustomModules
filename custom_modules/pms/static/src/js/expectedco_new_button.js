/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class ExpectedCOReportListController extends ListController {
    setup() {
        super.setup();
    }

    OnChangeExpectedCOReport() {
        this.actionService.doAction({
            name: 'Expected CO Wizard',
            type: 'ir.actions.act_window',
            res_model: 'expectedco.wizard',
            views: [[false, 'form']],
            target: 'new',
        });
    }
}

registry.category("views").add("button_in_expectedco_report_tree", {
    ...listView,
    Controller: ExpectedCOReportListController,
    buttonTemplate: "button_expectedco_report.ListView.Buttons",
});