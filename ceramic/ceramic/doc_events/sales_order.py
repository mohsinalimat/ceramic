from __future__ import unicode_literals
import frappe
from frappe import _

def on_submit(self):
    """On Submit Custom Function"""
    create_sales_order(self)

def on_update(self, method):
    for row in self.items:
        if row.rate == 0:
            frappe.throw(_("Rate can not be 0 in row {}".format(row.idx)))

def create_sales_order(self):
    def get_sales_order_doc(source_name, target_doc=None, ignore_permissions= True):
        def set_missing_values(source, target):
            target.company = "Millennium Vitrified Tiles Pvt. Ltd."
        
        doclist = get_mapped_doc("Sales Order", source_name, {
            "Sales Order Item": {
                "doctype": "Sales Order",
                "field_map": {
                    "rate": "dicounted_rate",
                    "qty": "billing_qty",
                },
            }
        }, target_doc, set_missing_values, ignore_permissions=ignore_permissions)
    
        return doclist
    
    so = get_sales_order_doc(self.name)

    try:
        so.save(ignore_permissions = True)
        so.submit()
    except Exception as e:
        frappe.db.rollback()
        frappe.throw(e)
    