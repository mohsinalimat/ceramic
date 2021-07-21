// Copyright (c) 2020, Finbyz and contributors
// For license information, please see license.txt

// cur_frm.fields_dict.primary_customer.get_query = function(doc) {
// 	return {
// 		filters: {
// 			"is_primary_customer":1 
// 		}
// 	}
// };

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
cur_frm.fields_dict.mode_of_payment.get_query = function (doc) {
	return {
		filters: [
			["authority",'!=', "Authorized"]
		]
	}
};
cur_frm.set_query("cost_center","deductions", function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	return{
		filters: [
			["company",'=',doc.company]
		]
	}
});
cur_frm.set_query("account","deductions", function(doc, cdt, cdn){
	var d = locals[cdt][cdn];
	return{
		filters: [
			["company",'=',doc.company],
			["is_group",'=',0]
		]
	}
});

this.frm.cscript.onload = function (frm) {
	this.frm.set_query("primary_customer", function (doc) {
		return { query: "ceramic.controllers.queries.new_customer_query" }
	});
}
frappe.ui.form.on('Primary Customer Payment', {
	 refresh: function(frm) {
		frm.events.hide_unhide_fields(frm);
		//frm.trigger('mode_of_payment')
	},
	company: function(frm){
		frm.trigger('mode_of_payment')
	},
	

	mode_of_payment: function(frm) {
		var me = this;
		get_payment_mode_account(frm, frm.doc.mode_of_payment, function(account){
			//var payment_account_field = frm.doc.payment_type == "Receive" ? "paid_to" : "paid_from";
			frm.set_value("paid_to", account);
		})
		if (frm.doc.deductions == undefined && frm.doc.mode_of_payment == "Shroff / Hawala") {
			frappe.db.get_value("Company", frm.doc.company, 'abbr', function (r) {

				let d = frm.add_child("deductions")
				d.account = "Hawala / Shroff Commision - " + r.abbr, 
					d.cost_center = "Main - " + r.abbr,
					d.amount = 0
			})
		}
		if(frm.doc.mode_of_payment=="Cash"){
			frm.set_df_property("reference_no", "reqd", "0");
			frm.set_df_property("reference_date", "reqd", "0");
			frm.refresh();
		}
		else{
			frm.set_df_property("reference_no", "reqd", "1");
			frm.set_df_property("reference_date", "reqd", "1");
			frm.refresh();
		}
	},
	
	
	primary_customer:function(frm){
		frm.refresh_fields()
		frm.doc.references = []
		frm.doc.total_allocated_amount = 0
		frm.doc.unallocated_amount = frm.doc.paid_amount
		frm.doc.difference_amount = 0
		if (frm.doc.mode_of_payment == "Shroff / Hawala"){
			frm.doc.deductions = []
			frappe.db.get_value("Company", frm.doc.company, 'abbr', function (r) {
				let d = frm.add_child("deductions")
				d.account = "Hawala / Shroff Commision - " + r.abbr, 
					d.cost_center = "Main - " + r.abbr,
					d.amount = 0
			})
		}
		
		frappe.db.get_value("Company",frm.doc.company,'default_receivable_account',function(r){
			if(r.default_receivable_account){
				frm.set_value('paid_from',r.default_receivable_account)
			}
		})
		frm.refresh_fields()
	},
	
	get_outstanding_invoice: function (frm) {
		frm.doc.references=[]
		if (!frm.doc.company) {
			frappe.throw('Please select company')
		}
		frm.trigger('get_primary_customer')
	},
	get_primary_customer:function(frm){
	var company_currency = frm.doc.company? frappe.get_doc(":Company", frm.doc.company).default_currency: "";

		var args = {
			"posting_date": frm.doc.posting_date,
			"company": frm.doc.company,
			"party_type": 'Customer',
			"payment_type": frm.doc.payment_type,
			"party_account": frm.doc.payment_type=="Receive" ? frm.doc.paid_from : frm.doc.paid_to,
			"cost_center": frm.doc.cost_center,
			"primary_customer": frm.doc.primary_customer
		}
		frappe.call({
			//method: 'erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents',
			// get primary customer 
			method: 'ceramic.ceramic.doctype.primary_customer_payment.primary_customer_payment.get_primary_customer_reference_documents',
			args: {
				args:args
			},
			callback: function(r, rt) {
				if(r.message) {
					var total_positive_outstanding = 0;
					var total_negative_outstanding = 0;
					
					// iterate loop over the invoices
					$.each(r.message, function (i, d) {
						var c = frm.add_child("references");
						c.reference_doctype = d.voucher_type;
						c.reference_name = d.voucher_no;
						c.due_date = d.due_date;
						c.customer = d.party;
						c.total_amount = d.invoice_amount;
						c.outstanding_amount = d.diff_amt;
						c.bill_no = d.bill_no;
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
					if(frm.doc.payment_type=="Receive" && frm.doc.primary_customer)
					{
						if(total_positive_outstanding > total_negative_outstanding)
							if (!frm.doc.paid_amount)
								frm.set_value("paid_amount",
									total_positive_outstanding - total_negative_outstanding);
					} else if (
						total_negative_outstanding &&
						total_positive_outstanding < total_negative_outstanding
					) {
						if (!frm.doc.received_amount)
							frm.set_value("received_amount",
								total_negative_outstanding - total_positive_outstanding);
					}
				}

				frm.events.allocate_party_amount_against_ref_docs(frm,
					(frm.doc.payment_type=="Receive" ? frm.doc.paid_amount : frm.doc.received_amount));
				}
		});					
	},

	// set Account paid_to and set account currency and account balance 
	paid_to: function(frm) {
		if(frm.set_party_account_based_on_party) return;

		frm.events.set_account_currency_and_balance(frm, frm.doc.paid_to,
			"paid_to_account_currency", "paid_to_account_balance", function(frm) {
				if (frm.doc.payment_type == "Receive") {
					if(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
						if(frm.doc.source_exchange_rate) {
							frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
						}
						frm.set_value("received_amount", frm.doc.paid_amount);

					} else {
						frm.events.received_amount(frm);
					}
				}
			}
		);
	},
	
	// set account details like account currency and account balance
	set_account_currency_and_balance: function(frm, account, currency_field,
		balance_field, callback_function) {
	if (frm.doc.posting_date && account) {
		frappe.call({
			method: 'ceramic.ceramic.doctype.primary_customer_payment.primary_customer_payment.get_account_details',
			args: {
				"account": account,
				"date": frm.doc.posting_date,
				"cost_center": frm.doc.cost_center
			},
			callback: function(r, rt) {
				if(r.message) {
					frappe.run_serially([
						() => frm.set_value(currency_field, r.message['account_currency']),
						() => {
							frm.set_value(balance_field, r.message['account_balance']);

							if(frm.doc.payment_type=="Receive" && currency_field=="paid_to_account_currency") {
								frm.toggle_reqd(["reference_no", "reference_date"],
									(r.message['account_type'] == "Bank" ? 1 : 0));
								if(!frm.doc.received_amount && frm.doc.paid_amount)
									frm.events.paid_amount(frm);
							}
							// } else if(frm.doc.payment_type=="Pay" && currency_field=="paid_from_account_currency") {
							// 	frm.toggle_reqd(["reference_no", "reference_date"],
							// 		(r.message['account_type'] == "Bank" ? 1 : 0));

							// 	if(!frm.doc.paid_amount && frm.doc.received_amount)
							// 		frm.events.received_amount(frm);
							// }
						},
						() => {
							if(callback_function) callback_function(frm);

							frm.events.hide_unhide_fields(frm);
						}
					]);
				}
			}
		});
	}
	},

	allocate_party_amount_against_ref_docs: function(frm, paid_amount) {
		var total_positive_outstanding_including_order = 0;
		var total_negative_outstanding = 0;
		var total_deductions = frappe.utils.sum($.map(frm.doc.deductions || [],
			function(d) { return flt(d.amount) }));
	
		//paid_amount = frm.doc.paid_amount
		paid_amount -= total_deductions;

		$.each(frm.doc.references || [], function(i, row) {
			if(flt(row.outstanding_amount) > 0)
				total_positive_outstanding_including_order += flt(row.outstanding_amount);
			else
				total_negative_outstanding += Math.abs(flt(row.outstanding_amount));
		})

		var allocated_negative_outstanding = 0;
		if (frm.doc.payment_type=="Receive" && frm.doc.primary_customer) {
				if(total_positive_outstanding_including_order > paid_amount) {
					var remaining_outstanding = total_positive_outstanding_including_order - paid_amount;
					allocated_negative_outstanding = total_negative_outstanding < remaining_outstanding ?
						total_negative_outstanding : remaining_outstanding;
			}

			var allocated_positive_outstanding =  paid_amount + allocated_negative_outstanding;
		} else if (in_list(["Customer", "Supplier"], frm.doc.primary_customer)) {
			if(paid_amount > total_negative_outstanding) {
				if(total_negative_outstanding == 0) {
					frappe.msgprint(__("Cannot {0} {1} {2} without any negative outstanding invoice",
						[frm.doc.payment_type,
							(frm.doc.primary_customer ? "to" : "from"), frm.doc.primary_customer]));
					return false
				} else {
					frappe.msgprint(__("Paid Amount cannot be greater than total negative outstanding amount {0}", [total_negative_outstanding]));
					return false;
				}
			} else {
				allocated_positive_outstanding = total_negative_outstanding - paid_amount;
				allocated_negative_outstanding = paid_amount +
					(total_positive_outstanding_including_order < allocated_positive_outstanding ?
						total_positive_outstanding_including_order : allocated_positive_outstanding)
			}
		}

		$.each(frm.doc.references || [], function(i, row) {
			row.allocated_amount = 0 //If allocate payment amount checkbox is unchecked, set zero to allocate amount
			if(frappe.flags.allocate_payment_amount != 0){
				if(row.outstanding_amount > 0 && allocated_positive_outstanding > 0) {
					if(row.outstanding_amount >= allocated_positive_outstanding) {
						row.allocated_amount = allocated_positive_outstanding;
					} else {
						row.allocated_amount = row.outstanding_amount;
					}

					allocated_positive_outstanding -= flt(row.allocated_amount);
				} else if (row.outstanding_amount < 0 && allocated_negative_outstanding) {
					if(Math.abs(row.outstanding_amount) >= allocated_negative_outstanding)
						row.allocated_amount = -1*allocated_negative_outstanding;
					else row.allocated_amount = row.outstanding_amount;

					allocated_negative_outstanding -= Math.abs(flt(row.allocated_amount));
				}
			}
		})

		frm.refresh_fields()
		frm.events.set_total_allocated_amount(frm);
	},

	// set total allocated amount
	set_total_allocated_amount: function(frm) {
		var total_allocated_amount = 0.0;
		$.each(frm.doc.references || [], function(i, row) {
			if (row.allocated_amount) {
				total_allocated_amount += flt(row.allocated_amount);
				
			}
		});
		frm.set_value("total_allocated_amount", Math.abs(total_allocated_amount));

		frm.events.set_unallocated_amount(frm);
	},

	// set unallocated amount if primary customer and if paid amount is > total allocated amount
	set_unallocated_amount: function(frm) {
		var unallocated_amount = 0;
		var total_deductions = frappe.utils.sum($.map(frm.doc.deductions || [],
			function(d) { return flt(d.amount) }));

		if(frm.doc.primary_customer) {
			if(frm.doc.payment_type == "Receive"
				&& frm.doc.total_allocated_amount < frm.doc.paid_amount + total_deductions) {
					unallocated_amount = (frm.doc.received_amount + total_deductions
						- frm.doc.total_allocated_amount);
			} 
		}
		frm.set_value("unallocated_amount", unallocated_amount);
		frm.trigger("set_difference_amount");
	},

	set_difference_amount: function(frm) {
		var difference_amount = 0;

		var party_amount = flt(frm.doc.total_allocated_amount) + flt(frm.doc.unallocated_amount);

		if(frm.doc.payment_type == "Receive") {
			difference_amount = party_amount - flt(frm.doc.received_amount);
		}

		var total_deductions = frappe.utils.sum($.map(frm.doc.deductions || [],
			function(d) { return flt(d.amount) }));

		frm.set_value("difference_amount", difference_amount - total_deductions);

		frm.events.hide_unhide_fields(frm);
	},

	unallocated_amount: function(frm) {
		frm.trigger("set_difference_amount");
	},

	validate_reference_document: function(frm, row) {
		var _validate = function(i, row) {
			if (!row.reference_doctype) {
				return;
			}

			if(frm.doc.primary_customer &&
				!in_list(["Sales Order", "Sales Invoice", "Journal Entry"], row.reference_doctype)
			) {
				frappe.model.set_value(row.doctype, row.name, "reference_doctype", null);
				frappe.msgprint(__("Row #{0}: Reference Document Type must be one of Sales Order, Sales Invoice or Journal Entry", [row.idx]));
				return false;
			}
		}

		if (row) {
			_validate(0, row);
		} else {
			$.each(frm.doc.vouchers || [], _validate);
		}
	},
	hide_unhide_fields: function(frm) {
		var company_currency = frm.doc.company? frappe.get_doc(":Company", frm.doc.company).default_currency: "";

		frm.toggle_display("source_exchange_rate",
			(frm.doc.paid_amount && frm.doc.paid_from_account_currency != company_currency));

		frm.toggle_display("target_exchange_rate", (frm.doc.received_amount &&
			frm.doc.paid_to_account_currency != company_currency &&
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency));

		frm.toggle_display("base_paid_amount", frm.doc.paid_from_account_currency != company_currency);

		frm.toggle_display("base_received_amount", (
			frm.doc.paid_to_account_currency != company_currency &&
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency 
			&& frm.doc.base_paid_amount != frm.doc.base_received_amount
		));

		frm.toggle_display("received_amount", (frm.doc.payment_type=="Internal Transfer" ||
			frm.doc.paid_from_account_currency != frm.doc.paid_to_account_currency))

		frm.toggle_display(["base_total_allocated_amount"],
			(frm.doc.paid_amount && frm.doc.received_amount && frm.doc.base_total_allocated_amount &&
			((frm.doc.payment_type=="Receive" && frm.doc.paid_from_account_currency != company_currency))));

		var party_amount = frm.doc.payment_type=="Receive" ?
			frm.doc.paid_amount : frm.doc.received_amount;

		frm.toggle_display("write_off_difference_amount", (frm.doc.difference_amount && frm.doc.primary_customer &&
				(frm.doc.total_allocated_amount > party_amount)));
		
		frm.refresh_fields();
	},
	paid_amount: function(frm) {
		frm.set_value("base_paid_amount", flt(frm.doc.paid_amount) * flt(frm.doc.source_exchange_rate));
		frm.trigger("reset_received_amount");
		frm.events.hide_unhide_fields(frm);
	},

	received_amount: function(frm) {
		frm.set_paid_amount_based_on_received_amount = true;

		if(!frm.doc.paid_amount && frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency) {
			frm.set_value("paid_amount", frm.doc.received_amount);

			if(frm.doc.target_exchange_rate) {
				frm.set_value("source_exchange_rate", frm.doc.target_exchange_rate);
			}
			frm.set_value("base_paid_amount", frm.doc.base_received_amount);
		}

		frm.set_value("base_received_amount",
			flt(frm.doc.received_amount) * flt(frm.doc.target_exchange_rate));

		if(frm.doc.payment_type == "Pay")
			frm.events.allocate_party_amount_against_ref_docs(frm, frm.doc.received_amount);
		else
			frm.events.set_unallocated_amount(frm);

		frm.set_paid_amount_based_on_received_amount = false;
		frm.events.hide_unhide_fields(frm);
	},
	
	reset_received_amount: function(frm) {
		if(!frm.set_paid_amount_based_on_received_amount &&
				(frm.doc.paid_from_account_currency == frm.doc.paid_to_account_currency)) {

			frm.set_value("received_amount", frm.doc.paid_amount);

			if(frm.doc.source_exchange_rate) {
				frm.set_value("target_exchange_rate", frm.doc.source_exchange_rate);
			}
			frm.set_value("base_received_amount", frm.doc.base_paid_amount);
		}

		if(frm.doc.payment_type == "Receive")
			frm.events.allocate_party_amount_against_ref_docs(frm, frm.doc.paid_amount);
		else
			frm.events.set_unallocated_amount(frm);
	},

	write_off_difference_amount: function(frm) {
		frm.events.set_deductions_entry(frm, "write_off_account");
	},

	set_deductions_entry: function(frm, account) {
		if(frm.doc.difference_amount) {
			frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_company_defaults",
				args: {
					company: frm.doc.company
				},
				callback: function(r, rt) {
					if(r.message) {
						var write_off_row = $.map(frm.doc["deductions"] || [], function(t) {
							return t.account==r.message[account] ? t : null; });

						var row = [];

						var difference_amount = flt(frm.doc.difference_amount,
							precision("difference_amount"));

						if (!write_off_row.length && difference_amount) {
							row = frm.add_child("deductions");
							row.account = r.message[account];
							row.cost_center = r.message["cost_center"];
						} else {
							row = write_off_row[0];
						}

						if (row) {
							row.amount = flt(row.amount) + difference_amount;
						}

						refresh_field("deductions");
						frm.refresh_fields()
						frm.events.set_unallocated_amount(frm);
						frm.events.set_difference_amount(frm);
						
					}
				}
			})
		}
	},

})

frappe.ui.form.on('Primary Customer Payment Deduction', {
	amount: function(frm) {
		frm.events.set_unallocated_amount(frm);
	},

	deductions_remove: function(frm) {
		frm.events.set_unallocated_amount(frm);
	}
})

frappe.ui.form.on('Primary Customer Payment Reference', {
	reference_doctype: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frm.events.validate_reference_document(frm, row);
	},

	reference_name: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.reference_name && row.reference_doctype) {
			return frappe.call({
				method: "erpnext.accounts.doctype.payment_entry.payment_entry.get_reference_details",
				args: {
					reference_doctype: row.reference_doctype,
					reference_name: row.reference_name,
					party_account_currency: frm.doc.payment_type=="Receive" ?
						frm.doc.paid_from_account_currency : frm.doc.paid_to_account_currency
				},
				callback: function(r, rt) {
					if(r.message) {
						$.each(r.message, function(field, value) {
							frappe.model.set_value(cdt, cdn, field, value);
						})

						let allocated_amount = frm.doc.unallocated_amount > row.outstanding_amount ?
							row.outstanding_amount : frm.doc.unallocated_amount;

						frappe.model.set_value(cdt, cdn, 'allocated_amount', allocated_amount);
						frm.refresh_fields();
					}
				}
			})
		}
	},

	allocated_amount: function(frm) {
		frm.events.set_total_allocated_amount(frm);
	},

	references_remove: function(frm) {
		frm.events.set_total_allocated_amount(frm);
	}
});

// throw message before select primary customer if company is not selected and set value in paid_to
var get_payment_mode_account = function(frm, mode_of_payment, callback) {
	if(!frm.doc.company) {
		frappe.throw(__("Please select the Company first"));
	}

	if(!mode_of_payment) {
		return;
	}

	return  frappe.call({
		method: "erpnext.accounts.doctype.sales_invoice.sales_invoice.get_bank_cash_account",
		args: {
			"mode_of_payment": mode_of_payment,
			"company": frm.doc.company
		},
		callback: function(r, rt) {
			if(r.message) {
				callback(r.message.account)
			}
		}
	});
}
