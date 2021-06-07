cur_frm.set_query('primary_customer', function () {
    return {
        filters: {
            'is_primary_customer': 1
        }
    }
});
cur_frm.set_query('territory', function () {
    return {
        filters: {
            'is_group': 0
        }
    }
});


frappe.ui.form.on('Customer', {
    is_primary_customer: function (frm) {
        if (frm.doc.is_primary_customer) {
            frm.set_value('primary_customer', frm.doc.name || frm.doc.customer_name)
        } else {
            frm.set_value('primary_customer', null)
        }
    },
    onload: function (frm) {
        frm.doc.sales_team.foreach(function(d){
            if(d.company_ && !d.company){
                frappe.db.get_value("Comapany",d.company_,"alterante_company",function(r){
                    frm.set_value("company",r.alterante_company)
                });
            }
            frm.refresh("sales_team")
        });
    },
        refresh: function (frm) {
        if (frm.doc.__onload && frm.doc.__onload.dashboard_info) {
            // frm.dashboard.stats_area_row.addClass('hidden');
            frm.dashboard.stats_area_row.find('.col-sm-6.indicator-column').addClass('hidden');
            frm.dashboard.stats_area_row.find('.flex-column.col-xs-6').addClass('hidden');
            var company_wise_info = frm.doc.__onload.dashboard_info;
            company_wise_info.forEach(function (info) {
                frm.dashboard.stats_area.removeClass('hidden');
                frm.dashboard.stats_area_row.addClass('flex');
                frm.dashboard.stats_area_row.css('flex-wrap', 'wrap');

                var color = info.total_unpaid ? 'orange' : 'green';

                var indicator = $('<div class="flex-column col-sm-6">' +
                    '<div style="margin-top:10px"><h6>' + info.company + '</h6></div>' +

                    '<div class="badge-link small" style="margin-bottom:10px"><span class="indicator blue">' +
                    'Annual Billing: ' + format_currency(info.billing_this_year, info.currency) + '</span></div>' +

                    '<div class="badge-link small" style="margin-bottom:10px">' +
                    '<span class="indicator ' + color + '">Total Unpaid: '
                    + format_currency(info.total_unpaid, info.currency) + '</span></div>' +


                    '</div>').appendTo(frm.dashboard.stats_area_row);

                if (info.loyalty_points) {
                    $('<div class="badge-link small" style="margin-bottom:10px"><span class="indicator blue">' +
                        'Loyalty Points: ' + info.loyalty_points + '</span></div>').appendTo(indicator);
                }

                return indicator;
            });
        }
        frm.add_custom_button(__('Party Ledger Ceramic'), function() {
            frappe.set_route('query-report', 'Party Ledger Ceramic',
                {party_type:'Customer', primary_customer:frm.doc.name});
        });
        frm.add_custom_button(__('Accounts Receivable Ceramic'), function() {
            frappe.set_route('query-report', 'Accounts Receivable Ceramic',
                {party_type:'Customer', primary_customer:frm.doc.name});
        });
        frm.remove_custom_button("Accounting Ledger");
        frm.remove_custom_button("Accounts Receivable");
        $(".form-inner-toolbar").find("button[data-label=Create]").css({"float":"right !important"})

    },
    add_indicator_for_multicompany: function (frm, info) {
        frm.dashboard.stats_area.removeClass('hidden');
        frm.dashboard.stats_area_row.addClass('flex');
        frm.dashboard.stats_area_row.css('flex-wrap', 'wrap');

        var color = info.total_unpaid ? 'orange' : 'green';

        var indicator = $('<div class="flex-column test">' +
            '<div style="margin-top:10px"><h6>' + info.company + '</h6></div>' +

            '<div class="badge-link small" style="margin-bottom:10px"><span class="indicator blue">' +
            'Annual Billing: ' + format_currency(info.billing_this_year, info.currency) + '</span></div>' +

            '<div class="badge-link small" style="margin-bottom:10px">' +
            '<span class="indicator ' + color + '">Total Unpaid: '
            + format_currency(info.total_unpaid, info.currency) + '</span></div>' +


            '</div>').appendTo(frm.dashboard.stats_area_row);

        if (info.loyalty_points) {
            $('<div class="badge-link small" style="margin-bottom:10px"><span class="indicator blue">' +
                'Loyalty Points: ' + info.loyalty_points + '</span></div>').appendTo(indicator);
        }

        return indicator;
    },
})

cur_frm.fields_dict.sales_team.grid.get_field("company_").get_query = function(doc) {
    return {
		"filters": {
            "authority":"Authorized"
        }
	};
};
