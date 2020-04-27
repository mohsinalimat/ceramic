erpnext.utils.update_child_items = function(opts) {
	const frm = opts.frm;
	const cannot_add_row = (typeof opts.cannot_add_row === 'undefined') ? true : opts.cannot_add_row;
	const child_docname = (typeof opts.cannot_add_row === 'undefined') ? "items" : opts.child_docname;
	this.data = [];
	let me = this;
	const dialog = new frappe.ui.Dialog({
		title: __("Update Items"),
		fields: [
			{
				fieldname: "trans_items",
				fieldtype: "Table",
				label: "Items",
				cannot_add_rows: cannot_add_row,
				in_place_edit: true,
				reqd: 1,
				data: this.data,
				get_data: () => {
					return this.data;
				},
				fields: [{
					fieldtype:'Data',
					fieldname:"docname",
					read_only: 1,
					hidden: 1,
				}, {
					fieldtype:'Link',
					fieldname:"item_code",
					options: 'Item',
					in_list_view: 1,
					read_only: 0,
					disabled: 0,
					label: __('Item Code'),
					change: function(){
						let trans_items = cur_dialog.fields_dict.trans_items;
						let me2 = this;
						if (this.doc.item_code){
							frappe.call({
								method: "ceramic.ceramic.doc_events.sales_order.get_rate_discounted_rate",
								args: {
									"item_code": this.doc.item_code,
									"customer": frm.doc.customer,
									"company": frm.doc.company
								},
								callback: function(r){
									if (r.message){
										me2.doc.rate = r.message.rate || '0';
										me2.doc.discounted_rate = r.message.discounted_rate || '0';

										trans_items.grid.refresh();
									}
								}
							});
						}
					}
				}, {
					fieldtype:'Float',
					fieldname:"qty",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					label: __('Qty')
				}, {
					fieldtype:'Float',
					fieldname:"real_qty",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					label: __('Real Qty')
				}, {
					fieldtype:'Currency',
					fieldname:"rate",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					label: __('Rate')
				}, {
					fieldtype:'Currency',
					fieldname:"discounted_rate",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					label: __('Discounted Rate')
				}]
			},
		],
		primary_action: function() {
			const trans_items = this.get_values()["trans_items"];
			frappe.call({
				method: 'ceramic.update_item.update_child_qty_rate',
				freeze: true,
				args: {
					'parent_doctype': frm.doc.doctype,
					'trans_items': trans_items,
					'parent_doctype_name': frm.doc.name,
					'child_docname': child_docname
				},
				callback: function() {
					frm.reload_doc();
				}
			});
			this.hide();
			refresh_field("items");
		},
		primary_action_label: __('Update')
	});

	frm.doc[opts.child_docname].forEach(d => {
		dialog.fields_dict.trans_items.df.data.push({
			"docname": d.name,
			"name": d.name,
			"item_code": d.item_code,
			"qty": d.qty,
			"rate": d.rate,
			"discounted_rate": d.discounted_rate,
			"real_qty": d.real_qty
		});
		this.data = dialog.fields_dict.trans_items.df.data;
		dialog.fields_dict.trans_items.grid.refresh();
	})
	dialog.show();
}

erpnext.selling.SalesOrderController = erpnext.selling.SalesOrderController.extend({
	refresh: function(doc, dt, dn) {
		var me = this;
		// FinByz Changes Start
		// this._super();
		// FinByz Changes Over
		let allow_delivery = false;

		if (doc.docstatus==1) {

			if(this.frm.has_perm("submit")) {
				if(doc.status === 'On Hold') {
				   // un-hold
				   this.frm.add_custom_button(__('Resume'), function() {
					   me.frm.cscript.update_status('Resume', 'Draft')
				   }, __("Status"));

				   if(flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
					   // close
					   this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
				   }
				}
			   	else if(doc.status === 'Closed') {
				   // un-close
				   this.frm.add_custom_button(__('Re-open'), function() {
					   me.frm.cscript.update_status('Re-open', 'Draft')
				   }, __("Status"));
			   }
			}
			if(doc.status !== 'Closed') {
				if(doc.status !== 'On Hold') {
					allow_delivery = this.frm.doc.items.some(item => item.delivered_by_supplier === 0 && item.qty > flt(item.delivered_qty))
						&& !this.frm.doc.skip_delivery_note

					if (this.frm.has_perm("submit")) {
						if(flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
							// hold
							this.frm.add_custom_button(__('Hold'), () => this.hold_sales_order(), __("Status"))
							// close
							this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
						}
					}

					this.frm.add_custom_button(__('Pick List'), () => this.create_pick_list(), __('Create'));

					// delivery note
					if(flt(doc.per_delivered, 6) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1 && allow_delivery) {
						this.frm.add_custom_button(__('Delivery Note'), () => this.make_delivery_note_based_on_delivery_date(), __('Create'));
						this.frm.add_custom_button(__('Work Order'), () => this.make_work_order(), __('Create'));
					}

					// FinByz Changes Start
					// sales invoice
					// if(flt(doc.per_billed, 6) < 100) {
					// 	this.frm.add_custom_button(__('Invoice'), () => me.make_sales_invoice(), __('Create'));
					// }
					// FinByz Changes End

					// material request
					if(!doc.order_type || ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1
						&& flt(doc.per_delivered, 6) < 100) {
						this.frm.add_custom_button(__('Material Request'), () => this.make_material_request(), __('Create'));
						this.frm.add_custom_button(__('Request for Raw Materials'), () => this.make_raw_material_request(), __('Create'));
					}

					// make purchase order
					// FinByz Changes Start
						// this.frm.add_custom_button(__('Purchase Order'), () => this.make_purchase_order(), __('Create'));
					// FinByz Changes End

					// maintenance
					// FinByz Changes Start
					// if(flt(doc.per_delivered, 2) < 100 &&
					// 		["Sales", "Shopping Cart"].indexOf(doc.order_type)===-1) {
					// 	this.frm.add_custom_button(__('Maintenance Visit'), () => this.make_maintenance_visit(), __('Create'));
					// 	this.frm.add_custom_button(__('Maintenance Schedule'), () => this.make_maintenance_schedule(), __('Create'));
					// }
					// FinByz Changes End

					// project
					// FinByz Changes Start
					// if(flt(doc.per_delivered, 2) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type)!==-1 && allow_delivery) {
					// 		this.frm.add_custom_button(__('Project'), () => this.make_project(), __('Create'));
					// }
					// FinByz Changes End

					if(!doc.auto_repeat) {
						this.frm.add_custom_button(__('Subscription'), function() {
							erpnext.utils.make_subscription(doc.doctype, doc.name)
						}, __('Create'))
					}

					if (doc.docstatus === 1 && !doc.inter_company_order_reference) {
						let me = this;
						frappe.model.with_doc("Customer", me.frm.doc.customer, () => {
							let customer = frappe.model.get_doc("Customer", me.frm.doc.customer);
							let internal = customer.is_internal_customer;
							let disabled = customer.disabled;
							if (internal === 1 && disabled === 0) {
								me.frm.add_custom_button("Inter Company Order", function() {
									me.make_inter_company_order();
								}, __('Create'));
							}
						});
					}
				}
				// payment request
				// FinByz Changes Start
				// if(flt(doc.per_billed)<100) {
				// 	this.frm.add_custom_button(__('Payment Request'), () => this.make_payment_request(), __('Create'));
				// 	this.frm.add_custom_button(__('Payment'), () => this.make_payment_entry(), __('Create'));
				// }
				// FinByz Changes End
				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Quotation'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						target: me.frm,
						setters: [
							{
								label: "Customer",
								fieldname: "party_name",
								fieldtype: "Link",
								options: "Customer",
								default: me.frm.doc.customer || undefined
							}
						],
						get_query_filters: {
							company: me.frm.doc.company,
							docstatus: 1,
							status: ["!=", "Lost"]
						}
					})
				}, __("Get items from"));
		}

		this.order_type(doc);
	},

	price_list_rate: function(doc, cdt, cdn){
		let d = locals[cdt][cdn];
		frappe.call({
			method: "ceramic.ceramic.doc_events.sales_order.get_rate_discounted_rate",
			args: {
				"item_code": d.item_code,
				"customer": doc.customer,
				"company": doc.company
			},
			callback: function(r){
				if (r.message){
					frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
					frappe.model.set_value(cdt, cdn, 'discounted_rate', r.message.discounted_rate);
				}
			}
		});

		this.calculate_taxes_and_totals();
	},
	discounted_rate: function(frm, cdt, cdn){
		this.calculate_taxes_and_totals();
	},
	calculate_taxes: function() {
		var me = this;
		this.frm.doc.rounding_adjustment = 0;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(this.frm.doc["taxes"] || [], function(i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.tax_amount, precision("tax_amount", tax));
			}
		});

		$.each(this.frm.doc["items"] || [], function(n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			$.each(me.frm.doc["taxes"] || [], function(i, tax) {
				// tax_amount represents the amount of tax for the current step
				var current_tax_amount = me.get_current_tax_amount(item, tax, item_tax_map);

				// Adjust divisional loss to the last item
				if (tax.charge_type == "Actual") {
					actual_tax_dict[tax.idx] -= current_tax_amount;
					if (n == me.frm.doc["items"].length - 1) {
						current_tax_amount += actual_tax_dict[tax.idx];
					}
				}

				// accumulate tax amount into tax.tax_amount
				if (tax.charge_type != "Actual" &&
					!(me.discount_amount_applied && me.frm.doc.apply_discount_on=="Grand Total")) {
					tax.tax_amount += current_tax_amount;
				}

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// tax amount after discount amount
				tax.tax_amount_after_discount_amount += current_tax_amount;

				// for buying
				if(tax.category) {
					// if just for valuation, do not add the tax amount in total
					// hence, setting it as 0 for further steps
					current_tax_amount = (tax.category == "Valuation") ? 0.0 : current_tax_amount;

					current_tax_amount *= (tax.add_deduct_tax == "Deduct") ? -1.0 : 1.0;
				}

				// note: grand_total_for_current_item contains the contribution of
				// item's amount, previously applied tax and the current tax on that item
				if(i==0) {
					tax.grand_total_for_current_item = flt(item.discounted_net_amount + current_tax_amount);
				} else {
					tax.grand_total_for_current_item =
						flt(me.frm.doc["taxes"][i-1].grand_total_for_current_item + current_tax_amount);
				}

				// set precision in the last item iteration
				if (n == me.frm.doc["items"].length - 1) {
					me.round_off_totals(tax);

					// in tax.total, accumulate grand total for each item
					me.set_cumulative_total(i, tax);

					me.set_in_company_currency(tax,
						["total", "tax_amount", "tax_amount_after_discount_amount"]);

					// adjust Discount Amount loss in last tax iteration
					if ((i == me.frm.doc["taxes"].length - 1) && me.discount_amount_applied
						&& me.frm.doc.apply_discount_on == "Grand Total" && me.frm.doc.discount_amount) {
						me.frm.doc.rounding_adjustment = flt(me.frm.doc.grand_total -
							flt(me.frm.doc.discount_amount) - tax.total, precision("rounding_adjustment"));
					}
				}
			});
		});
	},
	get_current_tax_amount: function(item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;

		if(tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.tax_amount, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.net_amount / this.frm.doc.net_total) * actual) : 0.0;

		} else if(tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.discounted_net_amount;
		} else if(tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if(tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		}

		this.set_item_wise_tax(item, tax, tax_rate, current_tax_amount);

		return current_tax_amount;
	},
})
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({ frm: cur_frm }));
this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: { 'is_sales_item': 1, 'authority': doc.authority }
		}
	});
}
cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company
		}
	}
};
frappe.ui.form.on('Sales Order', {
	onload: function(frm){
		frm.trigger('naming_series');
	},
	naming_series: function(frm) {
		if (frm.doc.__islocal && frm.doc.company && !frm.doc.amended_from){
			frappe.call({
				method: "ceramic.api.check_counter_series",
				args: {
					'name': frm.doc.naming_series,
					'company_series': frm.doc.company_series,
					'date': frm.doc.transaction_date,
				},
				callback: function(e) {
					frm.set_value("series_value", e.message);
				}
			});
		}
	},
	company: function(frm){
		frm.trigger('naming_series');
	},
	transaction_date: function(frm){
		frm.trigger('naming_series');
	}
})
frappe.ui.form.on("Sales Order Item", {
	discounted_rate: (frm, cdt, cdn) =>{
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'discounted_amount', d.discounted_rate * d.real_qty);
		frappe.model.set_value(cdt, cdn, 'discounted_net_amount', d.discounted_rate * d.real_qty);
	},
	real_qty: (frm, cdt, cdn) =>{
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'discounted_amount', d.discounted_rate * d.real_qty);
		frappe.model.set_value(cdt, cdn, 'discounted_net_amount', d.discounted_rate * d.real_qty);
	},
	qty: (frm, cdt, cdn) =>{
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'real_qty', d.qty);
	}
});