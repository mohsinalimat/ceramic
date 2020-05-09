import frappe
from frappe import _
from frappe.utils import flt

def get_invoice_dict(self, row=None):
	def get_item_dict():
		default_uom = frappe.db.get_single_value("Stock Settings", "stock_uom") or _("Nos")
		cost_center = frappe.get_cached_value('Company',  self.company,  "cost_center")
		if not cost_center:
			frappe.throw(
				_("Please set the Default Cost Center in {0} company.").format(frappe.bold(self.company))
			)
		rate = flt(row.outstanding_amount) / flt(row.qty)
		full_rate = flt(row.full_amount) / flt(row.qty)
		full_rate = full_rate if rate < full_rate else rate

		return frappe._dict({
			"uom": default_uom,
			"rate": rate or 0.0,
			"qty": row.qty,
			"full_qty": row.qty,
			"full_rate": full_rate or 0.0,
			"conversion_factor": 1.0,
			"item_name": row.item_name or "Opening Invoice Item",
			"description": row.item_name or "Opening Invoice Item",
			income_expense_account_field: row.temporary_opening_account,
			"cost_center": cost_center
		})

	if not row:
		return None

	party_type = "Customer"
	income_expense_account_field = "income_account"
	if self.invoice_type == "Purchase":
		party_type = "Supplier"
		income_expense_account_field = "expense_account"

	item = get_item_dict()

	args = frappe._dict({
		"items": [item],
		"is_opening": "Yes",
		"set_posting_time": 1,
		"company": self.company,
		"due_date": row.due_date,
		"posting_date": row.posting_date,
		frappe.scrub(party_type): row.party,
		"doctype": "Sales Invoice" if self.invoice_type == "Sales" else "Purchase Invoice",
		"currency": frappe.get_cached_value('Company',  self.company,  "default_currency")
	})

	if self.invoice_type == "Sales":
		args["is_pos"] = 0

	return args