cur_frm.fields_dict.items.grid.get_field("item_code").get_query = function(doc,cdt,cdn) {
	let d = locals[cdt][cdn];
	if(cur_frm.doc.authority == "Authorized"){
		return {
			filters: {
				"item_series": ['NOT IN', [null, '']],
			}
		}
	}else{
		return {
			filters: {
				"item_series": ['IN', [null, '']],
			}
		}
	}
		
};
// cur_frm.set_query("shipping_address_name", function () {
// 	return {
// 		query: "frappe.contacts.doctype.address.address.address_query",
// 		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
// 	};
// });

cur_frm.set_query("customer_address", function () {
	return {
		query: "frappe.contacts.doctype.address.address.address_query",
		filters: { link_doctype: "Customer", link_name: cur_frm.doc.customer }
	};
});
erpnext.stock.DeliveryNoteController = erpnext.stock.DeliveryNoteController.extend({
	refresh: function(doc, dt, dn) {
		var me = this;
		// this._super();
		if ((!doc.is_return) && (doc.status!="Closed" || this.frm.is_new())) {
			if (this.frm.doc.docstatus===0) {
				this.frm.add_custom_button(__('Sales Order'),
					function() {
						erpnext.utils.map_current_doc({
							method: "ceramic.ceramic.doc_events.sales_order.make_delivery_note",
							source_doctype: "Sales Order",
							target: me.frm,
							setters: {
								customer: me.frm.doc.customer || undefined,
							},
							get_query_filters: {
								docstatus: 1,
								status: ["not in", ["Closed", "On Hold"]],
								per_delivered: ["<", 99.99],
								company: me.frm.doc.company,
								project: me.frm.doc.project || undefined,
							}
						})
					}, __("Get items from"));
			}
		}

		if (!doc.is_return && doc.status!="Closed") {
			if(flt(doc.per_installed, 2) < 100 && doc.docstatus==1)
				this.frm.add_custom_button(__('Installation Note'), function() {
					me.make_installation_note() }, __('Create'));

			if (doc.docstatus==1) {
				this.frm.add_custom_button(__('Sales Return'), function() {
					me.make_sales_return() }, __('Create'));
			}

			if (doc.docstatus==1) {
				this.frm.add_custom_button(__('Delivery Trip'), function() {
					me.make_delivery_trip() }, __('Create'));
			}

			if(doc.docstatus==0 && !doc.__islocal) {
				this.frm.add_custom_button(__('Packing Slip'), function() {
					frappe.model.open_mapped_doc({
						method: "erpnext.stock.doctype.delivery_note.delivery_note.make_packing_slip",
						frm: me.frm
					}) }, __('Create'));
			}

			if (!doc.__islocal && doc.docstatus==1) {
				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (doc.docstatus==1) {
			this.show_stock_ledger();
			if (erpnext.is_perpetual_inventory_enabled(doc.company)) {
				this.show_general_ledger();
			}
			if (this.frm.has_perm("submit") && doc.status !== "Closed") {
				me.frm.add_custom_button(__("Close"), function() { me.close_delivery_note() },
					__("Status"))
			}
		}

		if(doc.docstatus==1 && !doc.is_return && doc.status!="Closed" && flt(doc.per_billed) < 100) {
			// show Make Invoice button only if Delivery Note is not created from Sales Invoice
			var from_sales_invoice = false;
			from_sales_invoice = me.frm.doc.items.some(function(item) {
				return item.against_sales_invoice ? true : false;
			});

			if(!from_sales_invoice) {
				this.frm.add_custom_button(__('Sales Invoice'), function() { me.make_sales_invoice_test() },
					__('Create'));
				// if(doc.discounted_grand_total != 0){
				// this.frm.add_custom_button(__('Sales Invoice'), function() {me.make_sales_invoice()}, 
				// 	__('Create'));
				// }
				// else{	
				// this.frm.add_custom_button(__('Sales Invoice Test'), function() { me.make_sales_invoice_test() },
				// 	__('Create'));
				// }
			}
		}

		if(doc.docstatus==1 && doc.status === "Closed" && this.frm.has_perm("submit")) {
			this.frm.add_custom_button(__('Reopen'), function() { me.reopen_delivery_note() },
				__("Status"))
		}
		erpnext.stock.delivery_note.set_print_hide(doc, dt, dn);

		if(doc.docstatus==1 && !doc.is_return && !doc.auto_repeat) {
			cur_frm.add_custom_button(__('Subscription'), function() {
				erpnext.utils.make_subscription(doc.doctype, doc.name)
			}, __('Create'))
		}
	},
    make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "ceramic.ceramic.doc_events.delivery_note.create_invoice",
			frm: this.frm
		});
	},
	// Finbyz Changes to override for Make Sales Invoice Test
	make_sales_invoice_test: function() {
		frappe.model.open_mapped_doc({
			method: "ceramic.ceramic.doc_events.delivery_note.create_invoice_test",
			frm: this.frm
		});
	}
});

$.extend(cur_frm.cscript, new erpnext.stock.DeliveryNoteController({frm: cur_frm}));

this.frm.cscript.onload = function (frm) {
	this.frm.set_query("batch_no", "items", function (doc, cdt, cdn) {
		let d = locals[cdt][cdn];
		if (!d.item_code) {
			frappe.msgprint(__("Please select Item Code"));
		}
		else if (!d.warehouse) {
			frappe.msgprint(__("Please select warehouse"));
		}
		else {
			return {
				query: "ceramic.query.get_batch_no",
				filters: {
					'item_code': d.item_code,
					'company': doc.company,
					'warehouse': d.warehouse
				}
			}
		}
	});
}
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
	this.frm.set_query("warehouse", "items", function (doc, cdt, cdn) {
		let d = locals[cdt][cdn];
		return {
			query: "ceramic.query.get_warehouse",
			filters: {
				'batch_no': d.batch_no,
				'item_code': d.item_code
			}
		}
	});
	this.frm.set_query("customer", function (doc) {
		return { query: "erpnext.controllers.queries.customer_query" }
	});
}
cur_frm.fields_dict.taxes_and_charges.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"tax_paid": doc.tax_paid || 0,
			"tax_category":doc.tax_category
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
cur_frm.fields_dict.invoice_company.get_query = function (doc) {
	return {
		filters: {
			"authority": 'Authorized'
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
frappe.ui.form.on('Delivery Note', {
	onload: function (frm) {
		if (frm.doc__islocal) {
			frappe.db.get_value("Company", frm.doc.company, 'alternate_company', function (r) {
				frm.set_value('invoice_company', r.alternate_company)
			})
		}
	},
	refresh: function(frm) {
		frappe.db.get_value("Company",frm.doc.company,"alternate_company",function(r){
			frm.fields_dict["si_ref"].get_query = function(doc) {
					return {
						filters: {
							"primary_customer":frm.doc.customer,
							"company":r.alternate_company,
							"si_ref":'',
							"docstatus":1,
							"posting_date":frm.doc.posting_date
						}
					};
				}
		})
		if (frm.doc__islocal == 1) {
			frappe.db.get_value("Company", frm.doc.company, 'alternate_company', function (r) {
				frm.set_value('invoice_company', r.alternate_company)
			})
		}
		frm.trigger('add_get_items_button')
		// if (frm.doc.tax_category && frm.doc.docstatus ==0) {
		// 	frm.trigger('get_taxes')
		// }
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
	},
	before_save: function (frm) {
		if (!frm.doc.primary_customer) {
			frm.set_value('primary_customer', frm.doc.customer)
		}
		// if(frm.doc.si_ref){
		// 	frappe.db.get_value("Sales Invoice",frm.doc.si_ref,["tax_paid","tax_category"], function(r){
		// 		if (frm.doc.tax_paid != r.tax_paid){
		// 			frm.set_value('tax_paid',r.tax_paid)
		// 		}
		// 		if(frm.doc.tax_category != r.tax_category){
		// 			frm.set_value('tax_category',r.tax_category)
		// 		} 
		// 	})
		// }
		frm.trigger('get_taxes');
	},

	before_submit: function(frm){
		if(!frm.doc.si_ref){
			return new Promise((resolve, reject) => {
				frappe.confirm(
					'Are you sure to Save this document without Sales Invoice?',
					function(){
						resolve();
					},
					function(){
						reject();
						window.close();
					}
				)
			})
		}
	},
	customer: function (frm) {
		if (frm.doc.customer){
			frappe.db.get_value("Customer", frm.doc.customer, 'primary_customer').then(function(r){
				frm.set_value("primary_customer", r.message.primary_customer)
			});
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from && frm.doc.__islocal){
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
	company: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
		
	},
	add_get_items_button: (frm) => {
		let get_query_filters = {
			docstatus: 1,
			customer: frm.doc.customer,
			company: frm.doc.company,
		};
	},
	calculate_total: function (frm) {
		let total_qty = 0.0
		let total_net_weight = 0.0

		frm.doc.items.forEach(function (d) {
			total_qty += flt(d.qty);
			//d.wastage_qty = flt(d.picked_qty - d.qty)
		});

		frm.set_value("total_qty", total_qty);
		frm.set_value("total_net_weight", total_net_weight);
		frm.set_value("material_weight", flt(frm.doc.final_weight - frm.doc.initial_weight));
	},
	final_weight: function (frm) {
		if (frm.doc.initial_weight) {	
			frm.set_value("material_weight", flt(frm.doc.final_weight - frm.doc.initial_weight));
		}
	},
	initial_weight: function (frm) {
		if (frm.doc.final_weight) {
			frm.set_value("material_weight", flt(frm.doc.final_weight - frm.doc.initial_weight));
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
		if(frm.doc.tax_category){
			console.log('called')
			frappe.call({
				method: "ceramic.ceramic.doc_events.sales_order.get_tax_template",
				args: {
					'tax_paid': frm.doc.tax_paid,
					'tax_category': frm.doc.tax_category,
					'company': frm.doc.company
				},
				callback: function (r) {
					if (r.message) {
						if(r.message != frm.doc.taxes_and_charges){
							frm.set_value('taxes_and_charges', r.message)
						}
					}
					else {
						frm.set_value('taxes_and_charges', null)
						frm.set_value('taxes', [])
					}
					frm.refresh_field("taxes");
				}
			})
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
							frm.set_value('regional_sales_manager',row.regional_sales_manager)
							frm.set_value('dispatch_person',row.sales_manager)
								let st = frm.add_child("sales_team");
								st.sales_person = row.sales_person
								st.contact_no = row.contact_no
								st.allocated_percentage = row.allocated_percentage
								st.allocated_amount = row.allocated_amount
								st.commission_rate = row.commission_rate
								st.incentives = row.incentives
								st.company = row.company
								st.regional_sales_manager = row.regional_sales_manager
								st.sales_manager = row.sales_manager
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
							frm.set_value('regional_sales_manager',row.regional_sales_manager)
							frm.set_value('dispatch_person',row.sales_manager)
							let st = frm.add_child("sales_team");
							st.sales_person = row.sales_person
							st.contact_no = row.contact_no
							st.allocated_percentage = row.allocated_percentage
							st.allocated_amount = row.allocated_amount
							st.commission_rate = row.commission_rate
							st.incentives = row.incentives
							st.company = row.company
							st.regional_sales_manager = row.regional_sales_manager
							st.sales_manager = row.sales_manager
						}
					})

					frm.refresh_field("sales_team");
				});
			}, 2000);
		}
	},
});
frappe.ui.form.on("Delivery Note Item", {
	qty: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		frm.events.calculate_total(frm)
	},
	sqf_rate: (frm, cdt, cdn) => {
		let d = locals[cdt][cdn];
		if(d.sqf_rate){
			frappe.model.set_value(cdt, cdn, 'rate', flt(d.sqf_rate * 15.5));
		}
	},
	stock_qty:function(frm,cdt,cdn){
        var doc=locals[cdt][cdn]
        if (doc.stock_qty && doc.qty){
        console.log(doc.stock_qty/doc.qty)
        frappe.model.set_value(cdt,cdn,"conversion_factor",doc.stock_qty/doc.qty)
		frm.refresh();
        }
    }
	// real_qty: function (frm, cdt, cdn) {
	// 	frm.events.calculate_total(frm)
	// },
	// qty: function (frm, cdt, cdn) {
	// 	let d = locals[cdt][cdn];
	// 	if (!d.against_sales_invoice && !d.against_pick_list){
	// 		frappe.call({
	// 			method: "ceramic.ceramic.doc_events.delivery_note.get_rate_discounted_rate",
	// 			args: {
	// 				"item_code": d.item_code,
	// 				"customer": frm.doc.customer,
	// 				"company": frm.doc.company,
	// 				"so_number": frm.doc.name || null
	// 			},
	// 			callback: function (r) {
	// 				if (r.message) {
	// 					if (!d.rate){
	// 						frappe.model.set_value(cdt, cdn, 'rate', r.message.rate);
	// 					}
	// 					if (!d.discounted_rate){
	// 						frappe.model.set_value(cdt, cdn, 'discounted_rate', r.message.discounted_rate);
	// 					}
	// 				}
	// 			}
	// 		});
	// 	}
	// },
});