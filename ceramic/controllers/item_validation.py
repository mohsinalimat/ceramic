import frappe
from frappe import _

@frappe.whitelist()
def validate_item_authority(self,method):
    for row in self.items:
        if row.item_code:
            if frappe.db.get_value("Item",row.item_code,'is_stock_item'):
                if frappe.db.get_value("Item", row.item_code, 'authority') != self.authority:
                    frappe.throw(_("Row:{0} Not allowed to create {1} for {2} in {3}, please ensure item/item_series has been selected correctly.".format(row.idx,self.doctype,row.item_code,self.company)))