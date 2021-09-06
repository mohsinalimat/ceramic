erpnext.accounts.SalesInvoiceController = erpnext.accounts.SalesInvoiceController.extend({
    refresh: function(doc, dt, dn) {
        const me = this;
        // FinByz Changes Start
        // this._super();
        // FinByz Changes End
        if (cur_frm.msgbox && cur_frm.msgbox.$wrapper.is(":visible")) {
            // hide new msgbox
            cur_frm.msgbox.hide();
        }

        this.frm.toggle_reqd("due_date", !this.frm.doc.is_return);

        if (this.frm.doc.is_return) {
            this.frm.return_print_format = "Sales Invoice Return";
        }

        this.show_general_ledger();

        if (doc.update_stock) this.show_stock_ledger();

        if (doc.docstatus == 1 && doc.outstanding_amount != 0 &&
            !(cint(doc.is_return) && doc.return_against)) {
            cur_frm.add_custom_button(__('Payment'),
                this.make_payment_entry, __('Create'));
            cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
        }

        if (doc.docstatus == 1 && !doc.is_return) {

            var is_delivered_by_supplier = false;

            is_delivered_by_supplier = cur_frm.doc.items.some(function(item) {
                return item.is_delivered_by_supplier ? true : false;
            })

            if (doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
                cur_frm.add_custom_button(__('Return / Credit Note'),
                    this.make_sales_return, __('Create'));
                cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
            }

            if (cint(doc.update_stock) != 1) {
                // show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
                var from_delivery_note = false;
                from_delivery_note = cur_frm.doc.items
                    .some(function(item) {
                        return item.delivery_note ? true : false;
                    });

                if (!from_delivery_note && !is_delivered_by_supplier) {
                    cur_frm.add_custom_button(__('Delivery'),
                        cur_frm.cscript['Make Delivery Note'], __('Create'));
                }
            }

            if (doc.outstanding_amount > 0) {
                cur_frm.add_custom_button(__('Payment Request'), function() {
                    me.make_payment_request();
                }, __('Create'));

                // FinByz Changes Start
                // cur_frm.add_custom_button(__('Invoice Discounting'), function() {
                // 	cur_frm.events.create_invoice_discounting(cur_frm);
                // }, __('Create'));
                // FinByz Change End
            }

            // FinByz Changes Start
            // if (doc.docstatus === 1) {
            // 	cur_frm.add_custom_button(__('Maintenance Schedule'), function () {
            // 		cur_frm.cscript.make_maintenance_schedule();
            // 	}, __('Create'));
            // }
            // FinByz Changes End

            if (!doc.auto_repeat) {
                cur_frm.add_custom_button(__('Subscription'), function() {
                    erpnext.utils.make_subscription(doc.doctype, doc.name)
                }, __('Create'))
            }
        }

        // Show buttons only when pos view is active
        if (cint(doc.docstatus == 0) && cur_frm.page.current_view_name !== "pos" && !doc.is_return) {
            this.frm.cscript.sales_order_btn();
            this.frm.cscript.delivery_note_btn();
            this.frm.cscript.quotation_btn();
        }

        this.set_default_print_format();
        if (doc.docstatus == 1 && !doc.inter_company_invoice_reference) {
            frappe.model.with_doc("Customer", me.frm.doc.customer, function() {
                var customer = frappe.model.get_doc("Customer", me.frm.doc.customer);
                var internal = customer.is_internal_customer;
                var disabled = customer.disabled;
                if (internal == 1 && disabled == 0) {
                    me.frm.add_custom_button("Inter Company Invoice", function() {
                        me.make_inter_company_invoice();
                    }, __('Create'));
                }
            });
        }
    }
});

$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({ frm: cur_frm }));
this.frm.cscript.onload = function(frm) {
    this.frm.set_query("item_code", "items", function(doc) {
        return {
            query: "erpnext.controllers.queries.item_query",
            filters: [

                ['is_sales_item', '=', 1],
                ['authority', 'in', ['', doc.authority]]
            ]
        }
    });
    this.frm.set_query("customer", function(doc) {
        return { query: "erpnext.controllers.queries.customer_query" }
    });
}
// cur_frm.set_query("shipping_address_name", function() {
//     return {
//         query: "frappe.contacts.doctype.address.address.address_query",
//         filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
//     };
// });

cur_frm.set_query("customer_address", function() {
    return {
        query: "frappe.contacts.doctype.address.address.address_query",
        filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
    };
});
cur_frm.fields_dict.items.grid.get_field("warehouse").get_query = function(doc) {
    return {
        filters: {
            "company": doc.company,
        }
    }
};
cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"tax_paid": doc.tax_paid || 0,
			"tax_category":doc.tax_category
		}
	}
};
cur_frm.fields_dict.customer.get_query = function(doc) {
    return {
        filters: {
            "disabled": 0
        }
    }
};
cur_frm.fields_dict.set_warehouse.get_query = function(doc) {
    return {
        filters: {
            "company": doc.company
        }
    }
};
frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        // if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
        // 	frm.set_value("si_ref", "");
        // }
        if (cur_frm.doc.company) {
            frappe.db.get_value("Company", cur_frm.doc.company, 'company_series', (r) => {
                if(frm.doc.company_series != r.company_series){
                    frm.set_value('company_series', r.company_series);
                }
            });
        }
        if (frm.doc.__islocal) {
            frm.trigger('naming_series');
        }
        frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);

        // user roles
        if (frappe.user_roles.includes('Local Admin')) {
            cur_frm.set_df_property("primary_customer", "allow_on_submit", 1);
        } else {
            cur_frm.set_df_property("primary_customer", "allow_on_submit", 0);
        }
        if (!frm.doc.cost_center) {
            frappe.db.get_value("Company", frm.doc.company, 'cost_center', function(r) {
                frm.set_value('cost_center', r.cost_center)
            })
        }
        frm.trigger('fetch_city');
        // if(frm.doc.docstatus == 0 && frm.doc.si_ref && frm.doc.name.includes("New Sales Invoice")){
        // 	frappe.db.get_value("Sales Invoice",frm.doc.si_ref,["company_series","naming_series","series_value"],function(r){
        // 		frm.set_value("naming_series",'A' + String(r.company_series) + r.naming_series)
        // 		frm.set_value("series_value",r.series_value)
        // 	})
        // }
    },
    onload: function (frm) {
        frm.ignore_doctypes_on_cancel_all = ['Sales Invoice'];
        if (frm.doc.irn_cancelled && frm.doc.irn && frm.doc.__islocal && frm.doc.amended_from){
            frm.set_value("irn",'')
            frm.set_value("irn_cancelled",0)
        }
        if (frm.doc.eway_bill_cancelled &&frm.doc.ewaybill && frm.doc.__islocal && frm.doc.amended_from){
            frm.set_value("ewaybill",'')
            frm.set_value("eway_bill_cancelled",0)
        }
		if(frm.doc.company && frm.doc.__islocal){
            frappe.db.get_value("Bank Account",{"company":frm.doc.company,"is_company_account":1,"is_default":1},"name", function(r){
                frm.set_value("bank_account",r.name);
            })
        }
        frm.trigger('fetch_city');
	},
    shipping_address_name: function(frm){
        frm.trigger('fetch_city');
    },
    fetch_city: function(frm){
      if (frm.doc.shipping_address_name && frm.doc.docstatus == 0){
        frappe.db.get_value("Address",frm.doc.shipping_address_name,"city", function(r){
            if (r.city != frm.doc.city){
                frm.set_value("city",r.city);
            }
        })          
      }  
    },
    customer: function(frm) {
        if (frm.doc.customer) {
            frm.set_value("primary_customer", '')
            frappe.db.get_value("Customer", frm.doc.customer, 'primary_customer').then(function(r) {
                frm.set_value("primary_customer", r.message.primary_customer)
            })
            if (!frm.doc.primary_customer) {
                setTimeout(function() {
                    frm.doc.sales_team = []
                    frappe.db.get_value("Company",frm.doc.company,"alternate_company", function(r){
                    frappe.model.with_doc("Customer", frm.doc.customer, function() {
                        
                        var cus_doc = frappe.model.get_doc("Customer", frm.doc.customer)
                        $.each(cus_doc.sales_team, function(index, row) {
                            if (row.company == frm.doc.company || row.company == r.alternate_company) {
                                frm.set_value('sales_head', row.sales_person)
                                if (!row.regional_sales_manager) {
                                    frm.set_value('regional_sales_manager', row.sales_person)
                                } else {
                                    frm.set_value('regional_sales_manager', row.regional_sales_manager)
                                }
                                frm.set_value('dispatch_person', row.sales_manager)

                                if (row.sales_person) {
                                    let st = frm.add_child("sales_team");
                                    st.sales_person = row.sales_person
                                    st.contact_no = row.contact_no
                                    st.allocated_percentage = row.allocated_percentage
                                    st.allocated_amount = row.allocated_amount
                                    st.commission_rate = row.commission_rate
                                    st.incentives = row.incentives
                                    st.company = row.company
                                    st.regional_sales_manager = frm.doc.regional_sales_manager
                                    st.sales_manager = row.sales_manager
                                }
                            }
                        })
                        frm.refresh_field("sales_team");
                    });
                })
                }, 1000);
            }
        }
    },
    primary_customer: function(frm) {
        if (frm.doc.primary_customer) {
            setTimeout(function() {
                frm.doc.sales_team = []
                frappe.db.get_value("Company",frm.doc.company,"alternate_company", function(r){
                frappe.model.with_doc("Customer", frm.doc.primary_customer, function() {
                    var cus_doc = frappe.model.get_doc("Customer", frm.doc.primary_customer)
                    $.each(cus_doc.sales_team, function(index, row) {
                        if (row.company == frm.doc.company) {
                            frm.set_value('sales_head', row.sales_person)
                            if (!row.regional_sales_manager) {
                                frm.set_value('regional_sales_manager', row.sales_person)
                            } else {
                                frm.set_value('regional_sales_manager', row.regional_sales_manager)
                            }
                            frm.set_value('dispatch_person', row.sales_manager)
                            if (row.sales_person) {
                                let st = frm.add_child("sales_team");
                                st.sales_person = row.sales_person
                                st.contact_no = row.contact_no
                                st.allocated_percentage = row.allocated_percentage
                                st.allocated_amount = row.allocated_amount
                                st.commission_rate = row.commission_rate
                                st.incentives = row.incentives
                                st.company = row.company
                                st.regional_sales_manager = frm.doc.regional_sales_manager
                                st.sales_manager = row.sales_manager
                            }
                        }
                    })

                    frm.refresh_field("sales_team");
                })
                });
            }, 2000);
        }
    },
    before_save: function(frm) {
        if (!frm.doc.primary_customer) {
            frm.set_value('primary_customer', frm.doc.customer)
        }
        frm.trigger('calculate_total');
    },
    validate: function(frm){
        frm.trigger('update_payment_terms_from_sales_order');
    },
    calculate_total: function(frm) {
        let total_qty = 0.0
        let total_net_weight = 0.0

        frm.doc.items.forEach(function(d) {
            total_qty += flt(d.qty);
            d.total_weight = flt(d.weight_per_unit * d.qty)
            total_net_weight += flt(d.weight_per_unit * d.qty)
        });

        frm.set_value("total_qty", total_qty);
        frm.set_value("total_net_weight", total_net_weight);
    },
    update_payment_terms_from_sales_order: function(frm){
        if (frm.doc.items[0].sales_order){
            frappe.db.get_value("Sales Order",frm.doc.items[0].sales_order,"payment_terms_template", function(r){
                if (frm.doc.payment_terms_template != r.payment_terms_template){
                    frm.set_value("payment_terms_template",r.payment_terms_template)
                }
            })            
        }
    },
    naming_series_: function(frm) {
        if (frm.doc.company && !frm.doc.amended_from) {
            frappe.call({
                method: "ceramic.api.check_counter_series",
                args: {
                    'name': frm.doc.naming_series,
                    'company_series': frm.doc.company_series,
                },
                callback: function(e) {
                    frm.set_value("series_value", e.message);
                }
            });
        }
    },
    naming_series: function(frm) {
        if (frm.doc.__islocal) {
            frm.trigger('naming_series_');
        }
    },

    company: function(frm) {
        if (frm.doc.__islocal) {
            frm.trigger('naming_series_');
        }
        frappe.db.get_value("Company", frm.doc.company, ['cost_center', 'default_income_account', 'abbr'], function(r) {
            frm.doc.items.forEach(function(row) {
                frappe.model.set_value(row.doctype, row.name, 'cost_center', r.cost_center)
                frappe.model.set_value(row.doctype, row.name, 'income_account', r.default_income_account)
            })

        })

        if(frm.doc.company){
            frappe.db.get_value("Bank Account",{"company":frm.doc.company,"is_company_account":1,"is_default":1},"name", function(r){
                if(r.name){
                    frm.set_value("bank_account",r.name);
                }
            })
        }

    },
    company_series: function(frm) {
        if (frm.doc.__islocal) {
            frm.trigger('naming_series');
        }
    },
	tax_category: function (frm) {
		frm.trigger('get_taxes')
	},
	tax_paid: function (frm) {
		if (frm.doc.tax_category) {
			frm.trigger('get_taxes')
		}
	},
	get_taxes: function (frm) {
		frappe.call({
			method: "ceramic.ceramic.doc_events.sales_order.get_tax_template",
			args: {
				'tax_paid': frm.doc.tax_paid,
				'tax_category': frm.doc.tax_category,
				'company': frm.doc.company
			},
			callback: function (r) {
				if (r.message) {
					frm.set_value('taxes_and_charges', r.message)
				}
				else {
					frm.set_value('taxes_and_charges', null)
					frm.set_value('taxes', [])
				}
				frm.refresh_field("taxes");
			}
		})
	},

});
frappe.ui.form.on("Sales Invoice Item", {
    qty: (frm, cdt, cdn) => {
        let d = locals[cdt][cdn];
        frm.events.calculate_total(frm)
        var doc=locals[cdt][cdn]
        if (doc.stock != doc.stock_uom){
        if (doc.stock_qty && doc.qty){
        console.log(doc.stock_qty/doc.qty)
        frappe.model.set_value(cdt,cdn,"conversion_factor",doc.stock_qty/doc.qty)
        frm.refresh();
        }
    }
    },
    sqf_rate: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		if(d.sqf_rate){
			frappe.model.set_value(cdt, cdn, 'rate', flt(d.sqf_rate * 15.5));
		}
	},
    weight_per_unit: function(frm, cdt, cdn) {
        frm.events.calculate_total(frm)
    },
    stock_qty:function(frm,cdt,cdn){
        var doc=locals[cdt][cdn]
        if (doc.stock != doc.stock_uom){
        if (doc.stock_qty && doc.qty){
        console.log(doc.stock_qty/doc.qty)
        frappe.model.set_value(cdt,cdn,"conversion_factor",doc.stock_qty/doc.qty)
        frm.refresh();
        }
    }
    }
});