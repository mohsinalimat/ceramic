erpnext.accounts.SalesInvoiceController = erpnext.accounts.SalesInvoiceController.extend({
	refresh: function(doc, dt, dn) {
		const me = this;
		// FinByz Changes Start
		// this._super();
		// FinByz Changes End
		if(cur_frm.msgbox && cur_frm.msgbox.$wrapper.is(":visible")) {
			// hide new msgbox
			cur_frm.msgbox.hide();
		}

		this.frm.toggle_reqd("due_date", !this.frm.doc.is_return);

		if (this.frm.doc.is_return) {
			this.frm.return_print_format = "Sales Invoice Return";
		}

		this.show_general_ledger();

		if(doc.update_stock) this.show_stock_ledger();

		if (doc.docstatus == 1 && doc.outstanding_amount!=0
			&& !(cint(doc.is_return) && doc.return_against)) {
			cur_frm.add_custom_button(__('Payment'),
				this.make_payment_entry, __('Create'));
			cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
		}

		if(doc.docstatus==1 && !doc.is_return) {

			var is_delivered_by_supplier = false;

			is_delivered_by_supplier = cur_frm.doc.items.some(function(item){
				return item.is_delivered_by_supplier ? true : false;
			})

			if(doc.outstanding_amount >= 0 || Math.abs(flt(doc.outstanding_amount)) < flt(doc.grand_total)) {
				cur_frm.add_custom_button(__('Return / Credit Note'),
					this.make_sales_return, __('Create'));
				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}

			if(cint(doc.update_stock)!=1) {
				// show Make Delivery Note button only if Sales Invoice is not created from Delivery Note
				var from_delivery_note = false;
				from_delivery_note = cur_frm.doc.items
					.some(function(item) {
						return item.delivery_note ? true : false;
					});

				if(!from_delivery_note && !is_delivered_by_supplier) {
					cur_frm.add_custom_button(__('Delivery'),
						cur_frm.cscript['Make Delivery Note'], __('Create'));
				}
			}

			if (doc.outstanding_amount>0) {
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

			if(!doc.auto_repeat) {
				cur_frm.add_custom_button(__('Subscription'), function() {
					erpnext.utils.make_subscription(doc.doctype, doc.name)
				}, __('Create'))
			}
		}

		// Show buttons only when pos view is active
		if (cint(doc.docstatus==0) && cur_frm.page.current_view_name!=="pos" && !doc.is_return) {
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

$.extend(cur_frm.cscript, new erpnext.accounts.SalesInvoiceController({frm: cur_frm}));
this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [

				['is_sales_item', '=', 1],
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
	this.frm.set_query("customer", function (doc) {
		return { query: "erpnext.controllers.queries.customer_query" }
	});
}
cur_frm.set_query("shipping_address_name", function () {
	return {
		query: "frappe.contacts.doctype.address.address.address_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};
});

cur_frm.set_query("customer_address", function () {
	return {
		query: "frappe.contacts.doctype.address.address.address_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};
});
cur_frm.fields_dict.items.grid.get_field("warehouse").get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
		}
	}
};
cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
cur_frm.fields_dict.customer.get_query = function (doc) {
	return {
		filters: {
			"disabled": 0
		}
	}
};
cur_frm.fields_dict.set_warehouse.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
frappe.ui.form.on('Sales Invoice', {
	refresh: function(frm){
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("si_ref", "");
		}
		if (cur_frm.doc.company){
			frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
				frm.set_value('company_series', r.company_series);
			});
		}
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
	},
	before_save: function (frm) {
		frm.trigger('calculate_total');
	},
	calculate_total: function (frm) {
		let total_qty = 0.0
		let total_net_weight = 0.0

		frm.doc.items.forEach(function (d) {
			total_qty += flt(d.qty);
			d.total_weight = flt(d.weight_per_unit * d.qty)
			total_net_weight += flt(d.weight_per_unit * d.qty)
		});

		frm.set_value("total_qty", total_qty);
		frm.set_value("total_net_weight", total_net_weight);
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
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
	company: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	company_series: function(frm){
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	
});
frappe.ui.form.on("Sales Invoice Item", {
	qty: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		frm.events.calculate_total(frm)
	},
	weight_per_unit: function (frm, cdt, cdn) {
		frm.events.calculate_total(frm)
	}
});
