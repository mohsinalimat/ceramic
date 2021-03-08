doc = frappe.new_doc("Custom Field")
doc.dt = "User"
doc.label = "Default User"
doc.insert_after = "enabled"
doc.fieldtype = "Check"
doc.insert(ignore_permissions=True)