import frappe
from frappe import _

def calculate_contribution(self):
    pass

def before_validate(self, method):
    from erpnext.controllers.selling_controller import SellingController
    SellingController.calculate_contribution = calculate_contribution

def validate(self, method):
    if self.is_primary_customer:
        self.primary_customer = self.name or self.customer_name