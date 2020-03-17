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
    onload_post_render: function(frm){
		frm.trigger('si_menu_hide');
	},
	on_submit: function(frm){
		frm.trigger('si_menu_hide');
	},
	si_menu_hide: function(frm){
		
		let $group = cur_frm.page.get_inner_group_button("Create");
				
		let li_length = $group.find("ul li");
		for (let i = 0; i < li_length.length -1; i++) {		
			var li = $group.find(".dropdown-menu").children("li")[i];
			if (li.getElementsByTagName("a")[0].innerHTML == "Sales Invoice")
				$group.find(".dropdown-menu").children("li")[i].remove();
		}
		
		if (!frm.doc.__islocal && frm.doc.docstatus == 1 && frm.doc.status != 'Cancelled') {
			frm.add_custom_button(__("Sales Invoice"), function () {
				frappe.model.open_mapped_doc({
					method: "ceramic.ceramic.doc_events.delivery_note.create_invoice",
                    frm: cur_frm
				})
			},
			__("Create"));
			frm.add_custom_button(__("Sales Invoice Test"), function () {
				frappe.model.open_mapped_doc({
					method: "erpnext.stock.doctype.delivery_note.delivery_note.make_sales_invoice",
					frm: cur_frm
				})
			},
			__("Create"));
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