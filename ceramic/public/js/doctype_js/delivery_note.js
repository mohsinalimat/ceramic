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

erpnext.stock.DeliveryNoteController = erpnext.stock.DeliveryNoteController.extend({
	refresh: function(doc, dt, dn) {
		var me = this;
		// this._super();
		if ((!doc.is_return) && (doc.status!="Closed" || this.frm.is_new())) {
			if (this.frm.doc.docstatus===0) {
				this.frm.add_custom_button(__('Sales Order'),
					function() {
						erpnext.utils.map_current_doc({
							method: "erpnext.selling.doctype.sales_order.sales_order.make_delivery_note",
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
				this.frm.add_custom_button(__('Sales Invoice'), function() {me.make_sales_invoice()}, 
					__('Create'));
				this.frm.add_custom_button(__('Sales Invoice Test'), function() { me.make_sales_invoice_test() },
					__('Create'));
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
			method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
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
					'warehouse': d.warehouse
				}
			}
		}
	});
}

frappe.ui.form.on('Delivery Note', {
	refresh: function(frm) {
		frm.trigger('add_get_items_button')
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
	},
	naming_series: function(frm) {
		if (frm.doc.company && !frm.doc.amended_from){
			console.log(1)
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
		frm.get_items_btn = frm.add_custom_button(__('Get Items From Pick List'), () => {
			if (!frm.doc.customer) {
				frappe.msgprint(__('Please select Customer first'));
				return;
			}
			erpnext.utils.map_current_doc({
				method: 'ceramic.ceramic.doc_events.pick_list.make_delivery_note',
				source_doctype: 'Pick List',
				target: frm,
				setters: {
					company: frm.doc.company,
					customer: frm.doc.customer
				},
				// date_field: 'transaction_date',
				get_query_filters: get_query_filters
			});
		});
	}
});
