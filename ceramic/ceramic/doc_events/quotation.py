import frappe

@frappe.whitelist()
def get_items_from_item_group():
    return frappe.get_list("Item Group",filters={'is_quotation_item':1},fields=['name','quotation_index','tile_size','tile_thickness','net_weight_per_box','tile_per_box','uom'],order_by='quotation_index asc',ignore_permissions=True)