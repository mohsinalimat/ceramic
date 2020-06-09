
this.frm.cscript.onload = function (frm) {	
	this.frm.set_query("party", function (doc) {
		if (doc.party_type == "Customer" || doc.party_type == "Supplier") {
			return {
				filters: {
					"disabled": 0
				}
			}
		};
	});
}

frappe.ui.form.on('Payment Entry', {
	refresh: function(frm){
		if (frm.doc.__islocal){
			if (cur_frm.doc.company){
				frappe.db.get_value("Company", cur_frm.doc.company, 'company_series',(r) => {
					frm.set_value('company_series', r.company_series);
				});
			}
			if (frm.doc.amended_from && frm.doc.__islocal && frm.doc.docstatus == 0 && frm.doc.authority == "Authorized"){
				frm.set_value('pe_ref', null);
			}
			frm.set_df_property("company", "read_only", (!frm.doc.__islocal || frm.doc.amended_from) ? 1 : 0);
			frm.trigger('company');
		}
	},
	customer: function(frm) {
		frappe.db.get_value("Customer", frm.doc.customer, 'primary_customer').then(function(r){
		    frm.set_value("primary_customer", r.message.primary_customer)
		});
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
		frm.trigger('mode_of_payment');
		frm.trigger('party');
	},
	mode_of_payment: function (frm) {
		if (frm.doc.deductions == undefined && frm.doc.mode_of_payment == "Shroff / Hawala") {
			frappe.db.get_value("Company", frm.doc.company, 'abbr', function (r) {
				
				let d = frm.add_child("deductions")
				d.account = "Hawala / Shroff Commision - " + r.abbr,
				d.cost_center = "Main - " + r.abbr,
				d.amount = 0
			})
		}
	},
	before_save: function (frm) {
		frm.trigger('get_sales_partner');
	 },
	party: function (frm) {
		frm.trigger('get_primary_customer')
	},
	get_outstanding_invoices: function (frm) {
		frm.trigger('get_sales_partner')
	},
	get_primary_customer: function (frm) {
		if (frm.doc.party_type == "Customer") {
			frappe.db.get_value("Customer", frm.doc.party, 'primary_customer', function (r) {
				if (r.primary_customer) {
					frm.set_value('primary_customer', r.primary_customer)
				}
			});
		}
	},
	get_sales_partner: function (frm) {
		frm.doc.references.forEach(function (d) {
			if (d.reference_doctype == "Sales Invoice") {
				frappe.db.get_value(d.reference_doctype, d.reference_name, 'sales_partner', function (r) {
					if (r.sales_partner) {
						d.sales_person = r.sales_partner
						frappe.model.set_value(d.doctype, d.name, 'sales_person', r.sales_partner)
					}
				});
			}
		})
	}
});