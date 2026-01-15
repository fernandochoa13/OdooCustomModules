/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { _t } from "@web/core/l10n/translation";
import { X2ManyField} from "@web/views/fields/x2many/x2many_field";
import { registry } from '@web/core/registry';
import { listView } from '@web/views/list/list_view';

export class AutoReconcileListBorder extends ListRenderer {
    static template = "auto-reconcile.listwborders"
    setup() {
        super.setup();
    }
}
registry.category("views").add("list_with_gray_borders", {
    ...listView,
    Renderer: AutoReconcileListBorder,
});

export class AutoReconcileX2Many extends X2ManyField {
    setup() {
        super.setup()
    }
    static components = { ...X2ManyField.components, AutoReconcileListBorder }
    static template = "auto-reconcile.x2manylistwborders"
}

AutoReconcileX2Many.components = { Pager, KanbanRenderer, ListRenderer };
AutoReconcileX2Many.props = {
    ...standardFieldProps,
    addLabel: { type: String, optional: true },
    editable: { type: String, optional: true },
};
AutoReconcileX2Many.supportedTypes = ["one2many", "many2many"];
AutoReconcileX2Many.displayName = _t("Relational table");
AutoReconcileX2Many.useSubView = true;
AutoReconcileX2Many.extractProps = ({ attrs }) => {
    return {
        addLabel: attrs["add-label"],
    };
};

registry.category("fields").add("one2manyreconcile", AutoReconcileX2Many);