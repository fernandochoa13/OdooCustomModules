/** @odoo-module **/

// UPGRADES: ui prettier, make a subcomponent for file card
// Extra addon: ANother addons for the enterprise version that accepts odoo spreadsheets
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { FileUploader } from "@web/views/fields/file_handler";
import { useService } from "@web/core/utils/hooks";

export class ReconcileWizard extends Component {
    setup() {
        this.state = useState({
            file1: false,
            file2: false,
            filetochange: false,
            readysubmit: false,
            file1_label: false,
            file2_label: false,
            net: true,
            file1_initial_balance: false,
            file2_initial_balance: false,
        });
        this.actionService = useService('action')
        this.orm = useService('orm')
    }
    static components = {FileUploader}
    // Function abrir archivo
    checkReadySubmit() {
        if (this.state.file1 != false && this.state.file2 != false) {
            this.state.readysubmit = true
        }
    }

    onUploadAttachmentClick(ev) {
        if (ev.target.getAttribute('filen') === 'file1') {
            this.state.filetochange = 'file1'
        }
        else if (ev.target.getAttribute('filen') === 'file2') {
            this.state.filetochange = 'file2'
        } 
    }

    onUploaded(data) {
        if (this.state.filetochange === 'file1') {
            this.state.file1 = data
        } else {
            this.state.file2 = data
        }
        this.checkReadySubmit()
    }

    // Function para seleccionar de odoo archivo

       

    // Function para submit
    async onSubmit() {
        if (this.state.file1_label == false) {
            this.state.file1_label = "file 1"
        }
        if (this.state.file2_label == false) {
            this.state.file2_label = "file 2"
        }
        const res = await this.orm.create("reconcile.history", [
            {
                name: "Reconciliation",
                fileone: this.state.file1.data,
                filetwo: this.state.file2.data,
                fileone_label: this.state.file1_label,
                filetwo_label: this.state.file2_label,
                df1_initial_balance: this.state.file1_initial_balance,
                df2_initial_balance: this.state.file2_initial_balance,
                net: this.state.net
            }
        ])

        this.ReRouteAction(res)

    }

    // if (type === "create") {
    //     const response = await this.orm.create(model, values);
    //     values[0].id = response[0];
    //     result = values;
    // }

    ReRouteAction(id) {
        this.actionService.doAction({
            name: 'Reconciliation View',
            type: 'ir.actions.act_window',
            res_model: 'reconcile.history',
            views: [[false, 'form']],
            target: 'current',
            res_id: id,
            context: {}
        })
    }

}
ReconcileWizard.template = "auto-reconcile.ReconcileWizard";

registry.category("actions").add("reconcile_wizard", ReconcileWizard);


// EXAMPLE
// registry.category("views").add("button_in_tree", {
//     ...listView,
//     Controller: SaleListController,
//     buttonTemplate: "button_back.ListView.Buttons",
// });