/** @odoo-module **/

import publicWidget from 'web.public.widget';
import { WebsiteSaleLayout } from 'website_sale.website_sale';

/*
* This file is not used because the list/grid option was disable from properties view
* */
publicWidget.registry.PropertiesWebsiteSale = WebsiteSaleLayout.extend({}, {
    _onApplyShopLayoutChange: function (ev) {
        this._super.apply(this, arguments);
        var clickedValue = $(ev.target).val();
        var isList = clickedValue === 'list';

        var $properties_grids = this.$('.properties_grid');
        var $properties_lists = this.$('.properties_list');

        if($properties_grids && $properties_lists) {
            if(isList) {
                $properties_grids.each(function() {
                    var $properties_grid = $(this);
                    $properties_grid.find('*').css('transition', 'none');
                    $properties_grid.toggleClass('ao_properties_hide', true);
                    void $properties_grid[0].offsetWidth;
                    $properties_grid.find('*').css('transition', '');
                });
                $properties_lists.each(function() {
                    var $properties_list = $(this);
                    $properties_list.find('*').css('transition', 'none');
                    $properties_list.toggleClass('ao_properties_hide', false);
                    void $properties_list[0].offsetWidth;
                    $properties_list.find('*').css('transition', '');
                });
            } else {
                $properties_grids.each(function() {
                    var $properties_grid = $(this);
                    $properties_grid.find('*').css('transition', 'none');
                    $properties_grid.toggleClass('ao_properties_hide', false);
                    void $properties_grid[0].offsetWidth;
                    $properties_grid.find('*').css('transition', '');
                });
                $properties_lists.each(function() {
                    var $properties_list = $(this);
                    $properties_list.find('*').css('transition', 'none');
                    $properties_list.toggleClass('ao_properties_hide', true);
                    void $properties_list[0].offsetWidth;
                    $properties_list.find('*').css('transition', '');
                });
            }
        }
    },
});

export default publicWidget.registry.PropertiesWebsiteSale;
