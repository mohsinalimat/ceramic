cur_frm.fields_dict.customer.get_query = function (doc) {
	return {
		filters: {
			"disabled": 0
		}
	}
};
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
erpnext.utils.update_child_items = function (opts) {
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
					fieldtype: 'Data',
					fieldname: "docname",
					read_only: 1,
					hidden: 1,
				}, {
					fieldtype: 'Link',
					fieldname: "item_code",
					options: 'Item',
					in_list_view: 1,
					read_only: 0,
					reqd: 1,
					disabled: 0,
					columns: 3,
					label: __('Item Code'),
				}, {
					fieldtype: 'Float',
					fieldname: "qty",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					columns: 1,
					label: __('Qty')
				}, {
					fieldtype: 'Float',
					fieldname: "real_qty",
					default: 0,
					read_only: 0,
					in_list_view: 0,
					columns: 1,
					label: __('Real Qty')
				}, {
					fieldtype: 'Currency',
					fieldname: "rate",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					// columns: 1,
					permlevel: 2,
					label: __('Rate')
				}, {
					fieldtype: 'Currency',
					fieldname: "discounted_rate",
					default: 0,
					read_only: 0,
					in_list_view: 1,
					// columns: 1,
					permlevel: 1,
					label: __('Discounted Rate')
				}]
			},
		],
		primary_action: function () {
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
				callback: function () {
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
	refresh: function (doc, dt, dn) {
		var me = this;
		// FinByz Changes Start
		// this._super();
		// FinByz Changes Over
		let allow_delivery = false;

		if (doc.docstatus == 1) {
			if (this.frm.doc.per_delivered == 0) {
				this.frm.add_custom_button(__('Unpick All'), () => this.unpick_all(this.frm.doc))
			}

			if (this.frm.has_perm("submit")) {
				if (doc.status === 'On Hold') {
					// un-hold
					this.frm.add_custom_button(__('Resume'), function () {
						me.frm.cscript.update_status('Resume', 'Draft')
					}, __("Status"));

					if (flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
						// close
						this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
					}
				}
				else if (doc.status === 'Closed') {
					// un-close
					this.frm.add_custom_button(__('Re-open'), function () {
						me.frm.cscript.update_status('Re-open', 'Draft')
					}, __("Status"));
				}
			}
			if (doc.status !== 'Closed') {
				if (doc.status !== 'On Hold') {
					allow_delivery = this.frm.doc.items.some(item => item.delivered_by_supplier === 0 && item.qty > flt(item.delivered_qty))
						&& !this.frm.doc.skip_delivery_note

					if (this.frm.has_perm("submit")) {
						if (flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
							// hold
							this.frm.add_custom_button(__('Hold'), () => this.hold_sales_order(), __("Status"))
							// close
							this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
						}
					}
					if (this.frm.doc.per_picked !== 100) {
						this.frm.add_custom_button(__('Pick List'), () => this.create_pick_list(), __('Create'));
					}

					// delivery note
					if (flt(doc.per_delivered, 6) < 100 && ["Sales", "Shopping Cart"].indexOf(doc.order_type) !== -1 && allow_delivery && doc.workflow_state == "Approved") {
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
					if (!doc.order_type || ["Sales", "Shopping Cart"].indexOf(doc.order_type) !== -1
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

					if (!doc.auto_repeat) {
						this.frm.add_custom_button(__('Subscription'), function () {
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
								me.frm.add_custom_button("Inter Company Order", function () {
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

		if (this.frm.doc.docstatus === 0) {
			this.frm.add_custom_button(__('Quotation'),
				function () {
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

	unpick_all: function (doc, dt, dn) {
		frappe.call({
			method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
			args: {
				'sales_order': doc.name
			},
			callback: function (r) {
				frappe.msgprint(r.message);
			}
		})
	},

	price_list_rate: function (doc, cdt, cdn) {
		let d = locals[cdt][cdn];
		frappe.call({
			method: "ceramic.ceramic.doc_events.sales_order.get_rate_discounted_rate",
			args: {
				"item_code": d.item_code,
				"customer": doc.customer,
				"company": doc.company,
				"so_number": doc.name || null
			},
			callback: function (r) {
				if (r.message) {
					frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
					frappe.model.set_value(cdt, cdn, 'discounted_rate', r.message.discounted_rate);
				}
			}
		});

		this.calculate_taxes_and_totals();
	},
	discounted_rate: function (frm, cdt, cdn) {
		this.calculate_taxes_and_totals();
	},
	calculate_taxes: function () {
		var me = this;
		this.frm.doc.rounding_adjustment = 0;
		var actual_tax_dict = {};

		// maintain actual tax rate based on idx
		$.each(this.frm.doc["taxes"] || [], function (i, tax) {
			if (tax.charge_type == "Actual") {
				actual_tax_dict[tax.idx] = flt(tax.tax_amount, precision("tax_amount", tax));
			}
		});

		$.each(this.frm.doc["items"] || [], function (n, item) {
			var item_tax_map = me._load_item_tax_rate(item.item_tax_rate);
			$.each(me.frm.doc["taxes"] || [], function (i, tax) {
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
					!(me.discount_amount_applied && me.frm.doc.apply_discount_on == "Grand Total")) {
					tax.tax_amount += current_tax_amount;
				}

				// store tax_amount for current item as it will be used for
				// charge type = 'On Previous Row Amount'
				tax.tax_amount_for_current_item = current_tax_amount;

				// tax amount after discount amount
				tax.tax_amount_after_discount_amount += current_tax_amount;

				// for buying
				if (tax.category) {
					// if just for valuation, do not add the tax amount in total
					// hence, setting it as 0 for further steps
					current_tax_amount = (tax.category == "Valuation") ? 0.0 : current_tax_amount;

					current_tax_amount *= (tax.add_deduct_tax == "Deduct") ? -1.0 : 1.0;
				}

				// note: grand_total_for_current_item contains the contribution of
				// item's amount, previously applied tax and the current tax on that item
				if (i == 0) {
					tax.grand_total_for_current_item = flt(item.discounted_net_amount + current_tax_amount);
				} else {
					tax.grand_total_for_current_item =
						flt(me.frm.doc["taxes"][i - 1].grand_total_for_current_item + current_tax_amount);
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
	get_current_tax_amount: function (item, tax, item_tax_map) {
		var tax_rate = this._get_tax_rate(tax, item_tax_map);
		var current_tax_amount = 0.0;

		if (tax.charge_type == "Actual") {
			// distribute the tax amount proportionally to each item row
			var actual = flt(tax.tax_amount, precision("tax_amount", tax));
			current_tax_amount = this.frm.doc.net_total ?
				((item.net_amount / this.frm.doc.net_total) * actual) : 0.0;

		} else if (tax.charge_type == "On Net Total") {
			current_tax_amount = (tax_rate / 100.0) * item.discounted_net_amount;
		} else if (tax.charge_type == "On Previous Row Amount") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].tax_amount_for_current_item;

		} else if (tax.charge_type == "On Previous Row Total") {
			current_tax_amount = (tax_rate / 100.0) *
				this.frm.doc["taxes"][cint(tax.row_id) - 1].grand_total_for_current_item;
		}

		this.set_item_wise_tax(item, tax, tax_rate, current_tax_amount);

		return current_tax_amount;
	},
	close_sales_order: function () {
		this.frm.cscript.update_status("Close", "Closed")
		frappe.call({
			method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
			args: {
				'sales_order': this.frm.doc.name,
			},
			callback: function (r) {
				frappe.msgprint(r.message);
			}
		})
	},
	// Finbyz Changes Start
	create_pick_list() {
		frappe.model.open_mapped_doc({
			method: "ceramic.ceramic.doc_events.sales_order.make_pick_list",
			frm: this.frm
		})
	},
	make_delivery_note_based_on_delivery_date: function() {
		var me = this;

		var delivery_dates = [];
		$.each(this.frm.doc.items || [], function(i, d) {
			if(!delivery_dates.includes(d.delivery_date)) {
				delivery_dates.push(d.delivery_date);
			}
		});

		var item_grid = this.frm.fields_dict["items"].grid;
		if(!item_grid.get_selected().length && delivery_dates.length > 1) {
			var dialog = new frappe.ui.Dialog({
				title: __("Select Items based on Delivery Date"),
				fields: [{fieldtype: "HTML", fieldname: "dates_html"}]
			});

			var html = $(`
				<div style="border: 1px solid #d1d8dd">
					<div class="list-item list-item--head">
						<div class="list-item__content list-item__content--flex-2">
							${__('Delivery Date')}
						</div>
					</div>
					${delivery_dates.map(date => `
						<div class="list-item">
							<div class="list-item__content list-item__content--flex-2">
								<label>
								<input type="checkbox" data-date="${date}" checked="checked"/>
								${frappe.datetime.str_to_user(date)}
								</label>
							</div>
						</div>
					`).join("")}
				</div>
			`);

			var wrapper = dialog.fields_dict.dates_html.$wrapper;
			wrapper.html(html);

			dialog.set_primary_action(__("Select"), function() {
				var dates = wrapper.find('input[type=checkbox]:checked')
					.map((i, el) => $(el).attr('data-date')).toArray();

				if(!dates) return;

				$.each(dates, function(i, d) {
					$.each(item_grid.grid_rows || [], function(j, row) {
						if(row.doc.delivery_date == d) {
							row.doc.__checked = 1;
						}
					});
				})
				me.make_delivery_note();
				dialog.hide();
			});
			dialog.show();
		} else {
			this.make_delivery_note();
		}
	},

	make_delivery_note: function() {
		frappe.model.open_mapped_doc({
			method: "ceramic.ceramic.doc_events.sales_order.make_delivery_note",
			frm: me.frm
		})
	},
	// Finbyz Changes End
})
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({ frm: cur_frm }));
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
	this.frm.set_query("primary_customer", function (doc) {
		return { query: "erpnext.controllers.queries.customer_query" }
	});

}
cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"tax_paid": doc.tax_paid || 0
		}
	}
};
cur_frm.fields_dict.items.grid.get_field("item_series").get_query = function (doc) {
	return {
		filters: {
			"authority": "Authorized",
		}
	}
}
cur_frm.set_query('primary_customer', function () {
	return {
		filters: {
			'is_primary_customer': 1
		}
	}
});
cur_frm.set_query('company', function () {
	return {
		filters: {
			'authority': "Unauthorized"
		}
	}
});
frappe.ui.form.on('Sales Order', {
	refresh: (frm) => {
		if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0){
			frm.set_value("so_ref", "");
		}
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
	},
	lotwise_balance: function(frm){
		window.open(window.location.href.split("#")[0] + "#query-report/Lot-Wise Balance" + "/?" + "company="+ frm.doc.company + "&" + "sales_order=" + frm.doc.name,"_blank")
	},
	onload: function (frm) {
		frm.trigger('naming_series');
		if(frm.doc.__islocal){
			frm.trigger('set_bank_account')
		
		}
		if (frm.doc.per_delivered > 0) {
			cur_frm.set_df_property("tax_category", "allow_on_submit", 0);
			cur_frm.set_df_property("tax_paid", "allow_on_submit", 0);
			cur_frm.set_df_property("taxes_and_charges", "allow_on_submit", 0);
		}
		if (frm.doc.docstatus == 1) {
			frm.add_custom_button(__("Change Customer"), function () {
				let me = this;
				let dialog = new frappe.ui.Dialog({
					'title': 'Change Customer',
					'fields': [
						{ fieldtype: "Link", fieldname: "old_customer", label: __('Old Customer'), options: "Customer", default: frm.doc.customer, read_only: 1 },
						{ fieldtype: "Link", fieldname: "new_customer", label: __('New Customer'), options: "Customer" },
					],
				});
				dialog.show();
				dialog.set_primary_action(__('Change'), function () {
					var values = dialog.get_values();
					frappe.call({
						method: "ceramic.ceramic.doc_events.sales_order.change_customer",
						args: {
							customer: values.new_customer,
							doc: frm.doc.name
						},
						callback: (r) => {
							if (r.message) {
								//frappe.msgprint('Customer changed successfully');
								dialog.hide();
								frm.reload_doc();
							}
						}
					})
				});
				dialog.get_close_btn().on('click', () => {
					dialog.hide();
				});
			});
		}
	},
	customer: function (frm) {
		if (frm.doc.customer) {
			frm.set_value("primary_customer", '')
			frappe.db.get_value("Customer", frm.doc.customer, 'primary_customer').then(function (r) {
				frm.set_value("primary_customer", r.message.primary_customer)
			})
			if (!frm.doc.primary_customer) {
				setTimeout(function () {
					frm.doc.sales_team = []
					frappe.model.with_doc("Customer", frm.doc.customer, function () {
						var cus_doc = frappe.model.get_doc("Customer", frm.doc.customer)
						$.each(cus_doc.sales_team, function (index, row) {
							if (row.company == frm.doc.company) {
							frm.set_value('sales_head',row.sales_person)
							if (!row.regional_sales_manager){
								frm.set_value('regional_sales_manager',row.sales_person)
							}
							else{
								frm.set_value('regional_sales_manager',row.regional_sales_manager)
							}
							frm.set_value('dispatch_person',row.sales_manager)
							
							if(row.sales_person){
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
				}, 1000);
			}
		}
	},
	primary_customer: function (frm) {
		if (frm.doc.primary_customer) {
			setTimeout(function () {
				frm.doc.sales_team = []
				frappe.model.with_doc("Customer", frm.doc.primary_customer, function () {
					var cus_doc = frappe.model.get_doc("Customer", frm.doc.primary_customer)
					$.each(cus_doc.sales_team, function (index, row) {
						if (row.company == frm.doc.company) {
							frm.set_value('sales_head',row.sales_person)
							if (!row.regional_sales_manager){
								frm.set_value('regional_sales_manager',row.sales_person)
							}
							else{
								frm.set_value('regional_sales_manager',row.regional_sales_manager)
							}
							frm.set_value('dispatch_person',row.sales_manager)

							if(row.sales_person){
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
			}, 2000);
		}
	},
	before_save: function (frm) {
		frm.trigger('calculate_total');
		if (!frm.doc.primary_customer) {
			frm.set_value('primary_customer', frm.doc.customer)
		}
	},
	set_bank_account: function(frm){
		frappe.db.get_value("Company",frm.doc.company, ['authority','alternate_company'],function(d)
		{	
			if( d.authority == 'Authorized')
			{
			frappe.db.get_value("Bank Account",{'company':frm.doc.company,'is_default':1},'name' ,function(r){
			frm.set_value('bank_account', r.name);
			})
			
			}
			else if( d.authority == 'Unauthorized') 
			{
			frappe.db.get_value("Bank Account",{'company':d.alternate_company,'is_default':1}, 'name' ,function(s){
			frm.set_value('bank_account', s.name);
			})
			}
		
	})

	},
	// naming_series: function (frm) {
	// 	if (frm.doc.__islocal && frm.doc.company && !frm.doc.amended_from) {
	// 		frappe.call({
	// 			method: "ceramic.api.check_counter_series",
	// 			args: {
	// 				'name': frm.doc.naming_series,
	// 				'company_series': frm.doc.company_series,
	// 				'date': frm.doc.transaction_date,
	// 			},
	// 			callback: function (e) {
	// 				frm.set_value("series_value", e.message);
	// 			}
	// 		});
	// 	}
	// },
	company: function (frm) {
		frm.trigger('naming_series');
		frm.trigger('set_bank_account');
		frm.trigger('order_priority');
	},
	delivery_date: function (frm) {
		$.each(frm.doc.items || [], function (i, d) {
			d.delivery_date = frm.doc.delivery_date;
		});
		refresh_field("items");
	},
	transaction_date: function (frm) {
		frm.trigger('naming_series');
	},
	calculate_total: function (frm) {
		let total_qty = 0.0
		let total_real_qty = 0.0
		let total_picked_qty = 0.0
		let total_picked_weight = 0.0
		let total_net_weight = 0.0

		frm.doc.items.forEach(function (d) {
			total_qty += flt(d.qty);
			total_real_qty += flt(d.real_qty);
			total_picked_qty += flt(d.picked_qty);
			d.picked_weight = flt(d.weight_per_unit * d.picked_qty)
			total_picked_weight += flt(d.picked_weight);
			d.total_weight = flt(d.weight_per_unit * d.qty)
			total_net_weight = flt(d.weight_per_unit * d.qty)
		});

		frm.set_value("total_qty", total_qty);
		frm.set_value("total_real_qty", total_real_qty);
		frm.set_value("total_picked_qty", total_picked_qty);
		frm.set_value("total_picked_weight", total_picked_weight);
	},
	update_items: function (frm) {
		erpnext.utils.update_child_items({
			frm: frm,
			child_docname: "items",
			child_doctype: "Sales Order Detail",
			cannot_add_row: false,
		})
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
	transaction_date: function(frm){
		frm.trigger('order_priority')
	},
	order_priority: function(frm){
		if (frm.doc.order_priority && frm.doc.company && frm.doc.transaction_date){
			frappe.call({
				method: "ceramic.ceramic.doc_events.sales_order.update_order_rank_",
				args: {
					'date': frm.doc.transaction_date,
					'order_priority': frm.doc.order_priority,
					'company': frm.doc.company
				},
				callback: function (r) {
					if (r.message){
						frm.set_value('order_item_priority', r.message.order_item_priority)
						frm.set_value('order_rank', r.message.order_rank)
					}
				}
			})
		}
	},
	before_workflow_action: function (frm) {
		if (frm.doc.workflow_state == 'Applied') {

			frm.doc.items.forEach(function (d) {
				if (!d.rate) {
					frappe.throw(__("Row:{0} Rate can not be zero", [d.idx]))
				}
			})
		}
	},
	correct_picked_qty: function (frm) {
		frm.doc.items.forEach(function (d) {
			frappe.call({
				method: "ceramic.ceramic.doc_events.pick_list.correct_picked_qty",
				args: {
					'sales_order': frm.doc.name
				},
				callback: function (r) {
					//frappe.msgprint(r.message);
				}
			})
		});
	}
});
frappe.ui.form.on("Sales Order Item", {
	items_add: function (frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		row.delivery_date = frm.doc.delivery_date;
		frm.refresh_field("items");
	},
	sqf_rate: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		if(d.sqf_rate){
			frappe.model.set_value(cdt, cdn, 'rate', flt(d.sqf_rate * 15.5));
		}
	},
	discounted_rate: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'discounted_amount', d.discounted_rate * d.real_qty);
		frappe.model.set_value(cdt, cdn, 'discounted_net_amount', d.discounted_rate * d.real_qty);
	},
	real_qty: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'discounted_amount', d.discounted_rate * d.real_qty);
		frappe.model.set_value(cdt, cdn, 'discounted_net_amount', d.discounted_rate * d.real_qty);
	},
	qty: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, 'real_qty', d.qty);
		frm.events.calculate_total(frm)
	},
	real_qty: function (frm, cdt, cdn) {
		frm.events.calculate_total(frm)
	},
	unpick_item: function (frm, cdt, cdn) {
		let d = locals[cdt][cdn]
			
		// frappe.call({
		// 	method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
		// 	args: {
		// 		'sales_order': frm.doc.name,
		// 		'sales_order_item': d.name,
		// 	},
		// 	callback: function (r) {
		// 		frappe.msgprint(r.message);
		// 	}
		// })
		
		frappe.call({
			method: "ceramic.ceramic.doc_events.pick_list.unpick_item",
			args: {
				'sales_order': frm.doc.name,
				'sales_order_item': d.name,
				'item_code':d.item_code
			},
			callback: function (r) {
				frappe.msgprint(r.message);
				frappe.call({
					method: "ceramic.ceramic.doc_events.pick_list.correct_picked_qty",
					args: {
						'sales_order': frm.doc.name,
					}
				})
			}
		})
	}
});

cur_frm.fields_dict.sales_team.grid.get_field("company_").get_query = function(doc) {
    return {
        "filters": [
                ["authority", "in", ["Authorized"]]
        ]
    };
};