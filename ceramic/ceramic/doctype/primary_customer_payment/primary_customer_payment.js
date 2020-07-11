// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

cur_frm.fields_dict.primary_customer.get_query = function(doc) {
	return {
		filters: {
			"is_primary_customer":1 
		}
	}
};
cur_frm.fields_dict.company.get_query = function (doc) {
	return {
		filters: {
			"authority": "Unauthorized"
		}
	}
};
cur_frm.fields_dict.paid_from.get_query = function (doc) {
	return {
		filters: {
			"company": doc.company,
			"is_group":0,
			"account_type":'Payable'
		}
	}
};
cur_frm.fields_dict.paid_to.get_query = function (doc) {
	return {
		filters:[
			["company",'=',doc.company],
			["is_group",'=',0],
			['account_type','in',['Bank','Cash']]
		]	
	}
};

frappe.ui.form.on('Primary Customer Payment', {
	// refresh: function(frm) {

	// }
	primary_customer:function(frm){
		frappe.db.get_value("Company",frm.doc.company,'default_receivable_account',function(r){
			if(r.default_receivable_account){
				frm.set_value('paid_from',r.default_receivable_account)
			}
		})
	},
	
	get_outstanding_invoice: function (frm) {
		if (!frm.doc.company) {
			frappe.throw('Please select company')
		}
		frm.trigger('get_primary_customer')
	},
	get_primary_customer:function(frm){
		frappe.call({
			method:'frappe.client.get_list',
			args:
			{
				doctype:'Customer',
				filters:{
					'primary_customer':frm.doc.customer
				}
			},
			callback:function(m){
				if (m.message){	
					console.log(m.message)
					var company_currency = frappe.get_doc(":Company", frm.doc.company).default_currency;

					$.each(m.message, function(k, y) {
						if (y.name!='Administrator')
						{
							console.log(y.name)
						
						var args = {
							"posting_date": frm.doc.posting_date,
							"company": frm.doc.company,
							"party_type": 'Customer',
							"payment_type": frm.doc.payment_type,
							"party": y.name,
							"party_account": frm.doc.payment_type=="Receive" ? frm.doc.paid_from : frm.doc.paid_to,
							"cost_center": frm.doc.cost_center
						}
						frappe.call({
							//method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents',
							method: 'ceramic.ceramic.doctype.primary_customer_payment.primary_customer_payment.get_outstanding_reference_documents',
							args: {
								args:args
							},
							callback: function(r, rt) {
								if(r.message) {
									var total_positive_outstanding = 0;
									var total_negative_outstanding = 0;
				
									$.each(r.message, function (i, d) {
										console.log(d.voucher_type)
										var c = frm.add_child("references");
										c.reference_doctype = d.voucher_type;
										c.reference_name = d.voucher_no;
										c.due_date = d.due_date
										c.total_amount = d.invoice_amount;
										c.outstanding_amount = d.outstanding_amount;
										c.bill_no = d.bill_no;
										console.log(c)
										frm.refresh_field('references')
										if(!in_list(["Sales Order", "Purchase Order", "Expense Claim", "Fees"], d.voucher_type)) {
											if(flt(d.outstanding_amount) > 0)
												total_positive_outstanding += flt(d.outstanding_amount);
											else
												total_negative_outstanding += Math.abs(flt(d.outstanding_amount));
										}
				
										var party_account_currency = frm.doc.payment_type=="Receive" ?
											frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency;
				
										if(party_account_currency != company_currency) {
											c.exchange_rate = d.exchange_rate;
										} else {
											c.exchange_rate = 1;
										}
										if (in_list(['Sales Invoice', 'Purchase Invoice', "Expense Claim", "Fees"], d.reference_doctype)){
											c.due_date = d.due_date;
										}
									})
								}
							}
					});
				}
					})
					
				}
			}
		})
	},
});
