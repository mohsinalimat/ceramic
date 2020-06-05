import frappe

@frappe.whitelist()
def get_items_from_item_group():
    return frappe.get_list("Item Group",{'is_quotation_item':1})
    