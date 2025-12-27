/** @odoo-module */
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { ListController } from '@web/views/list/list_controller';
import { registry } from '@web/core/registry';
import { kanbanView } from '@web/views/kanban/kanban_view';
import { listView } from '@web/views/list/list_view';



export class SaleKanbanController extends KanbanController {
    setup() {
        super.setup();
    }
    GoBack() {
        this.actionService.doAction({
            type: 'ir.actions.act_url',
            url: '/web',
            target: 'self'
        });
    }
    NewOrder() {
    const orderCreator = this.props.context.default_order_creator;
    this.actionService.doAction({
        name: 'New Material Order',
        type: 'ir.actions.act_window',
        res_model: 'create.order.wizard',
        views: [[false, 'form']],
        target: 'fullscreen',
        context: {
            'default_order_creator': orderCreator,
            }
        });
    };
}

registry.category("views").add("button_in_kanban", {
    ...kanbanView,
    Controller: SaleKanbanController,
    buttonTemplate: "button_back.KanbanView.Buttons",
});

// 'name': 'New Material Order',
// 'type': 'ir.actions.act_window',
// 'res_model': 'create.order.wizard',
// 'view_mode': 'form',
// 'view_id': form_view.id,
// 'target': 'fullscreen',
// self.env.ref('create_material_orders.create_order_wizard_form')

export class SaleListController extends ListController {
    setup() {
        super.setup();
    }

    GoBack() {
        this.actionService.doAction({
            type: 'ir.actions.act_url',
            url: '/web',
            target: 'self'
        });
    }

    NewOrder() {
        const orderCreator = this.props.context.default_order_creator;
        this.actionService.doAction({
            name: 'New Material Order',
            type: 'ir.actions.act_window',
            res_model: 'create.order.wizard',
            views: [[false, 'form']],
            target: 'fullscreen',
            context: {
                'default_order_creator': orderCreator,
            }
        });
    };

}

registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: SaleListController,
    buttonTemplate: "button_back.ListView.Buttons",
});