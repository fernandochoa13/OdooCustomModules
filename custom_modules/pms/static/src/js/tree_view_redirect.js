/** @odoo-module */

import { ListController } from "@web/views/list/list_controller";
// import { listView } from "@web/views/list/list_view";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class CustomInvoiceReportController extends ListController {
  setup() {
    super.setup();
    this.actionService = useService("action");
  }

//   ...listView,

  async openRecord(record) {
    console.log("InvoiceReportListController: openRecord called with record:");

    if (record.resModel === "account.move" && record.resId) {
      await this.actionService.doAction({
        type: "ir.actions.act_window",
        res_model: "account.move",
        res_id: record.resId,
        views: [[false, "form"]],
        target: "current",
      });

      await this.model.root.load();

      this.model.notify();
    } else {
      super.openRecord(record);
    }
  }
};

registry.category("views").add("click_view_invoice_report_tree", {
  Controller: CustomInvoiceReportController,
});

// registry.category("views").add("view_invoice_report_tree", {
//     ...listView,
//     Controller: CustomInvoiceReportController,
// });


// class InvoiceReportListController extends ListController {
//     async openRecord(record) {
//         console.log("InvoiceReportListController: openRecord called with record:", record);
//         const moveId = record.data.res_id;
//         console.log("InvoiceReportListController: moveId:", moveId);
//         const resModel = 'account.move';

//         console.log("InvoiceReportListController: moveId found, opening account.move form");
//         this.actionService.doAction({
//             type: 'ir.actions.act_window',
//             name: 'view_move_form',
//             res_model: resModel,
//             res_id: moveId,
//             view_mode: 'form',
//             view_type: 'form',
//         });
//         super.openRecord(record);
//     }
// }

// registry.category("views").add("view_invoice_report_tree", {
//     ...listView,
//     Controller: InvoiceReportListController,
// });

// class InvoiceReportListController extends ListController {
//   // setup() {
//   //     super.setup();
//   // }

//   async selectRecord() {
//     this.notificationService.add(
//       sprintf(this.env._t("Test 1")),
//       { title: this.env._t("Warning") }
//       // if (this.archInfo.openAction) {
//       // this.actionService.doActionButton({
//       //     name: this.archInfo.openAction.action,
//       //     type: this.archInfo.openAction.type,
//       //     resModel: record.resModel,
//       //     resId: record.resId,
//       //     resIds: record.resIds,
//       //     context: record.context,
//       //     onClose: async () => {
//       //         await record.model.root.load();
//       //         record.model.notify();
//       //     },
//       // });
//       // } else {
//       // const activeIds = this.model.root.records.map((datapoint) => datapoint.resId);
//       // this.props.selectRecord(record.resId, { activeIds });
//       // }
//     );
//   }
//   async openRecord() {
//     this.notificationService.add(sprintf(this.env._t("Test 2")), {
//       title: this.env._t("Warning"),
//       //     console.log("InvoiceReportListController: openRecord called with record:", record);
//       //     // const moveId = record.data.res_id;
//       //     // console.log("InvoiceReportListController: moveId:", moveId);
//       //     const resModel = 'account.move';

//       //     console.log("InvoiceReportListController: moveId found, opening account.move form");
//       //     this.actionService.doAction({
//       //         type: 'ir.actions.act_window',
//       //         name: 'view_move_form',
//       //         res_model: resModel,
//       //         // res_id: moveId,
//       //         view_mode: 'form',
//       //         view_type: 'form',
//       //     });
//     });
//   }
// }

// registry.category("views").add("view_invoice_report_tree", {
//   ...listView,
//   Controller: InvoiceReportListController,
// });
