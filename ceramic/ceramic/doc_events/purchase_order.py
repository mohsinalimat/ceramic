import frappe
from frappe import _

def before_validate(self, method):
	for item in self.items:
		item.discounted_amount = item.discounted_rate * item.real_qty
		item.discounted_net_amount = item.discounted_amount
	
def on_submit(self, method):
	check_rate_qty(self)

def check_rate_qty(self):
	for item in self.items:
		if not item.rate or item.rate <= 0:
			frappe.throw(f"Row: {item.idx} Rate cannot be 0 or less")
		if not item.qty or item.qty <= 0:
			frappe.throw(f"Row: {item.idx} Quantity can not be 0 or less")