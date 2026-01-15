/** @odoo-module */
import { ListController } from "@web/views/list/list_controller";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';


export class AutoReconcileListController extends ListController {
    setup() {
        super.setup();
    }

    OnCreateReconcile() {
        this.actionService.doAction('auto-reconcile.reconcile_wizard_action')
    
    }
}

registry.category("views").add("button_in_reconcile_history", {
    ...listView,
    Controller: AutoReconcileListController,
    buttonTemplate: "button_create_reconcile.ListView.Buttons",
});

