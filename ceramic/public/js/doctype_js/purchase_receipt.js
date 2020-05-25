cur_frm.fields_dict.taxes_and_charges.get_query = function(doc) {
	return {
		filters: {
			"docstatus": 0 && 1,
			"company": doc.company
		}
	}
};

erpnext.stock.PurchaseReceiptController = erpnext.stock.PurchaseReceiptController.extend({
	refresh: function(doc, dt, dn) {
		var me = this;
		if(doc.docstatus===1) {
			this.show_stock_ledger();
			//removed for temporary
			this.show_general_ledger();

			this.frm.add_custom_button(__('Asset'), function() {
				frappe.route_options = {
					purchase_receipt: me.frm.doc.name,
				};
				frappe.set_route("List", "Asset");
			}, __("View"));

			this.frm.add_custom_button(__('Asset Movement'), function() {
				frappe.route_options = {
					reference_name: me.frm.doc.name,
				};
				frappe.set_route("List", "Asset Movement");
			}, __("View"));
		}

		if(!doc.is_return && doc.status!="Closed") {
			if (doc.docstatus == 0) {
				this.frm.add_custom_button(__('Purchase Order'),
					function () {
						erpnext.utils.map_current_doc({
							method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_receipt",
							source_doctype: "Purchase Order",
							target: me.frm,
							setters: {
								supplier: me.frm.doc.supplier || undefined,
							},
							get_query_filters: {
								docstatus: 1,
								status: ["not in", ["Closed", "On Hold"]],
								per_received: ["<", 99.99],
								company: me.frm.doc.company
							}
						})
					}, __("Get items from"));
			}

			if(doc.docstatus == 1 && doc.status!="Closed") {
				if (this.frm.has_perm("submit")) {
					cur_frm.add_custom_button(__("Close"), this.close_purchase_receipt, __("Status"))
				}

				cur_frm.add_custom_button(__('Purchase Return'), this.make_purchase_return, __('Create'));

				cur_frm.add_custom_button(__('Make Stock Entry'), cur_frm.cscript['Make Stock Entry'], __('Create'));

				if(flt(doc.per_billed) < 100) {
					this.frm.add_custom_button(__('Purchase Invoice'), function() {me.make_purchase_invoice()}, 
					__('Create'));
					this.frm.add_custom_button(__('Purchase Invoice Test'), function() {me.make_purchase_invoice_test()}, 
					__('Create'));
				}
				cur_frm.add_custom_button(__('Retention Stock Entry'), this.make_retention_stock_entry, __('Create'));

				if(!doc.auto_repeat) {
					cur_frm.add_custom_button(__('Subscription'), function() {
						erpnext.utils.make_subscription(me.frm.doc.doctype, me.frm.doc.name)
					}, __('Create'))
				}

				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}


		if(doc.docstatus==1 && doc.status === "Closed" && this.frm.has_perm("submit")) {
			cur_frm.add_custom_button(__('Reopen'), this.reopen_purchase_receipt, __("Status"))
		}

		this.frm.toggle_reqd("supplier_warehouse", doc.is_subcontracted==="Yes");
	},
	make_purchase_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "ceramic.ceramic.doc_events.purchase_receipt.make_purchase_invoice",
			frm: cur_frm
		})
	},

	make_purchase_invoice_test: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.purchase_receipt.purchase_receipt.make_purchase_invoice",
			frm: cur_frm
		})
	},
})

$.extend(cur_frm.cscript, new erpnext.stock.PurchaseReceiptController({ frm: cur_frm }));

this.frm.cscript.onload = function (frm) {
	this.frm.set_query("item_code", "items", function (doc) {
		return {
			query: "erpnext.controllers.queries.item_query",
			filters: [

				['is_purchase_item', '=', 1],
				['authority', 'in', ['', doc.authority]]
			]
		}
	});
}
frappe.ui.form.on('Purchase Receipt', {
	refresh: function(frm) {
		if (frm.doc.__islocal){
			frm.trigger('naming_series');
		}
		frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
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
	}
});