/** @odoo-module */

import {IntegerField} from "@web/views/fields/integer/integer_field";
import {patch} from "@web/core/utils/patch";

patch(IntegerField.prototype, {
    get formattedValue() {
        if (!this.props.formatNumber) {
            return this.props.value;
        }
        return super.formattedValue;
    },
});

Object.assign(IntegerField.props, {
    formatNumber: {type: Boolean, optional: true},
});
Object.assign(IntegerField.defaultProps, {
    formatNumber: true,
});
const superExtractProps = IntegerField.extractProps;
IntegerField.extractProps = ({attrs}) => {
    return {
        ...superExtractProps({attrs}),
        formatNumber:
            attrs.options.enable_formatting === undefined
                ? true
                : Boolean(attrs.options.enable_formatting),
    };
};
