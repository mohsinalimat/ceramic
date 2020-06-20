import frappe

from frappe.utils import flt, cint, nowdate

from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address

def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = item.discounted_rate * item.real_qty
		item.discounted_net_amount = item.discounted_amount

def get_invoiced_qty_map(purchase_receipt):
	"""returns a map: {pr_detail: invoiced_qty}"""
	invoiced_qty_map = {}

	for pr_detail, qty in frappe.db.sql("""select pr_detail, qty from `tabPurchase Invoice Item`
		where purchase_receipt=%s and docstatus=1""", purchase_receipt):
			if not invoiced_qty_map.get(pr_detail):
				invoiced_qty_map[pr_detail] = 0
			invoiced_qty_map[pr_detail] += qty

	return invoiced_qty_map

def get_returned_qty_map(purchase_receipt):
	"""returns a map: {so_detail: returned_qty}"""
	returned_qty_map = frappe._dict(frappe.db.sql("""select pr_item.item_code, sum(abs(pr_item.qty)) as qty
		from `tabPurchase Receipt Item` pr_item, `tabPurchase Receipt` pr
		where pr.name = pr_item.parent
			and pr.docstatus = 1
			and pr.is_return = 1
			and pr.return_against = %s
		group by pr_item.item_code
	""", purchase_receipt))

	return returned_qty_map

@frappe.whitelist()
def make_purchase_invoice(source_name, target_doc=None):
	doc = frappe.get_doc('Purchase Receipt', source_name)
	returned_qty_map = get_returned_qty_map(source_name)
	invoiced_qty_map = get_invoiced_qty_map(source_name)

	def set_missing_values(source, target):
		if len(target.get("items")) == 0:
			frappe.throw(_("All items have already been invoiced"))

		doc = frappe.get_doc(target)
		doc.ignore_pricing_rule = 1
		doc.run_method("onload")
		doc.run_method("set_missing_values")
		doc.run_method("calculate_taxes_and_totals")
		target.update_stock = 1
		target.expense_account = ""

		alternate_company = frappe.db.get_value("Company", source.company, "alternate_company")

		if alternate_company:
			target.company = alternate_company

		target_company_abbr = frappe.db.get_value("Company", target.company, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source.company, "abbr")

		if source.set_warehouse:
			target.set_warehouse = source.set_warehouse.replace(source_company_abbr, target_company_abbr)
		
		if source.taxes_and_charges:
			taxes_and_charges = source.taxes_and_charges.replace(source_company_abbr, target_company_abbr)
			if frappe.db.exists("Purchase Taxes and Charges", taxes_and_charges):
				target.taxes_and_charges = taxes_and_charges
			else:
				target.taxes_and_charges = None
		target.taxes = source.taxes
		if source.taxes:
			for index, value in enumerate(source.taxes):
				target.taxes[index].account_head = source.taxes[index].account_head.replace(source_company_abbr, target_company_abbr)
				# frappe.throw(source_company_abbr + target_company_abbr)
				if source.taxes[index].cost_center:
					target.taxes[index].cost_center = source.taxes[index].cost_center.replace(source_company_abbr, target_company_abbr)
		target.credit_to = frappe.db.get_value("Company", alternate_company, 'default_payable_account')
		doc.run_method("calculate_taxes_and_totals")

	def update_item(source_doc, target_doc, source_parent):
		target_company = frappe.db.get_value("Company", source_parent.company, "alternate_company")

		doc = frappe.get_doc("Company", target_company)

		target_company_abbr = frappe.db.get_value("Company", target_company, "abbr")
		source_company_abbr = frappe.db.get_value("Company", source_parent.company, "abbr")

		if source_doc.expense_account:
			target_doc.expense_account = source_doc.expense_account.replace(source_company_abbr, target_company_abbr)
		if source_doc.cost_center:
			target_doc.cost_center = source_doc.cost_center.replace(source_company_abbr, target_company_abbr)

		if source_doc.warehouse:
			target_doc.warehouse = source_doc.warehouse.replace(source_company_abbr, target_company_abbr)


	def get_pending_qty(item_row):
		pending_qty = item_row.qty - invoiced_qty_map.get(item_row.name, 0)
		returned_qty = flt(returned_qty_map.get(item_row.item_code, 0))
		if returned_qty:
			if returned_qty >= pending_qty:
				pending_qty = 0
				returned_qty -= pending_qty
			else:
				pending_qty -= returned_qty
				returned_qty = 0
		return pending_qty, returned_qty


	doclist = get_mapped_doc("Purchase Receipt", source_name,	{
		"Purchase Receipt": {
			"doctype": "Purchase Invoice",
			"field_map": {
				"supplier_warehouse":"supplier_warehouse",
				"is_return": "is_return"
			},
			"validation": {
				"docstatus": ["=", 1],
			},
		},
		"Purchase Receipt Item": {
			"doctype": "Purchase Invoice Item",
			"field_map": {
				"item_code": "item_design",
				"item_series": "item_code",
				"parent": "purchase_receipt_docname",
				"name":"purchase_receipt_childname",
				"purchase_order_item": "po_childname",
				"purchase_order": "po_docname",
				"is_fixed_asset": "is_fixed_asset",
				"asset_location": "asset_location",
				"asset_category": 'asset_category',
				# Rate
				"discounted_rate": "rate",
				"rate":"full_rate",
				# Quantity
				"real_qty": "qty",
				"received_real_qty": "received_qty",
				"rejected_real_qty": "rejected_qty",
				"qty": "full_qty",
				"received_qty": "received_full_qty",
				"rejected_qty": "rejected_full_qty",
			},
			"field_no_map": [
				"income_account",
				"expense_account",
				"cost_center",
				"warehouse",
			],
			"postprocess": update_item,
		},
		"Purchase Taxes and Charges": {
			"doctype": "Purchase Taxes and Charges",
			"add_if_empty": True
		}
	}, target_doc, set_missing_values)

	return doclist