/** @odoo-module */

import {FloatField} from "@web/views/fields/float/float_field";
import {patch} from "@web/core/utils/patch";

patch(FloatField.prototype, {
    get formattedValue() {
        if (!this.props.formatNumber) {
            return this.props.value;
        }
        return super.formattedValue;
    },
});

Object.assign(FloatField.props, {
    formatNumber: {type: Boolean, optional: true},
});
Object.assign(FloatField.defaultProps, {
    formatNumber: true,
});
const superExtractProps = FloatField.extractProps;
FloatField.extractProps = ({attrs, field}) => {
    return {
        ...superExtractProps({attrs, field}),
        formatNumber:
            attrs.options.enable_formatting === undefined
                ? true
                : Boolean(attrs.options.enable_formatting),
    };
};
