import frappe
from frappe import _

def validate(self,method):
	validate_customer_group(self)

def validate_customer_group(self):
	if self.customer_group:
		if frappe.db.get_value("Customer Group",self.customer_group,'is_group'):
			frappe.throw(_("Please select proper customer group"))
	if self.territory:
		if frappe.db.get_value("Territory",self.territory,'is_group'):
			frappe.throw(_("Please select proper territory"))