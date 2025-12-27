/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ReportRenderer } from "@account_reports/components/report_renderer/report_renderer";
import { useService } from "@web/core/utils/hooks";

patch(ReportRenderer.prototype, {
    // Add event handlers after the component is mounted
    mounted() {
        super.mounted();
        this.el.addEventListener('click', this._onRefreshCashData.bind(this));
    },

    // Method to handle the button click
    _onRefreshCashData(ev) {
        if (!ev.target.classList.contains('refresh_cash_data_button')) {
            return;
        }

        const actionService = useService("action");
        const rpc = useService("rpc");
        
        // Disable the button to prevent multiple clicks
        ev.target.disabled = true;

        // Execute the Python function via RPC
        rpc.query({
            model: 'account.report',
            method: '_cleanup_cash_basis_data',
            args: [this.props.report_id] // Pass the report ID as 'self' in the Python method
        }).then(() => {
            // Re-enable the button
            ev.target.disabled = false;
            
            // Reload the report data after cleanup
            this.trigger('reload'); 
            
            // Show a success notification
            this.notification.add(this.env._t('Cash Basis Data has been successfully refreshed.'), {
                type: 'success',
            });
        }).catch(error => {
            // Re-enable the button and show error
            ev.target.disabled = false;
            this.notification.add(this.env._t('An error occurred while refreshing Cash Basis Data.'), {
                type: 'danger',
            });
            console.error(error);
        });
    },
});