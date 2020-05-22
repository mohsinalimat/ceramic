import frappe
from frappe import _

def validate(self, method):
    if self.is_primary_customer:
        self.primary_customer = self.name or self.customer_name