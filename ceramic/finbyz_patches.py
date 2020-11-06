# Patch In GL Entry for Updating Cost Center in MVTT
data = frappe.get_list("GL Entry",{'company':'Millennium Vitrified Tiles Pvt. Ltd. Testing','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MVTT')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))

# Patch In GL Entry for Updating Cost Center in MVT
data = frappe.get_list("GL Entry",{'company':'Millennium Vitrified Tiles Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MVT')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))

# Patch In GL Entry for Updating Cost Center in MCTT
data = frappe.get_list("GL Entry",{'company':'Millennium Cera Tiles Pvt. Ltd. Testing','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MCTT')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))


# Patch In GL Entry for Updating Cost Center in LVTPL
data = frappe.get_list("GL Entry",{'company':'Lorenzo Vitrified Tiles Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - LVTPL')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name))


# Patch In GL Entry for Updating Cost Center in MGI
data = frappe.get_list("GL Entry",{'company':'Maruti Gold Industries','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - MGI')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 

# Patch In GL Entry for Updating Cost Center in VF
data = frappe.get_list("GL Entry",{'company':'Victory Floor Tiles Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - VF')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 

# Patch In GL Entry for Updating Cost Center in KC
data = frappe.get_list("GL Entry",{'company':'Koradiya Ceramics Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - KC')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 


query = frappe.db.sql("""
    select pe.name
    from `tabPayment Entry` as pe JOIN
    `tabGL Entry` as gl on gl.voucher_no = pe.name
    where
        gl.voucher_type = 'Payment Entry'
        and (gl.account LIKE '%Debtors%' or gl.account LIKE '%Creditors%')
        and pe.paid_amount * 1.2 < (gl.debit + gl.credit) 
""")

# cost_center Patch
query = frappe.get_list("Purchase Invoice",{'cost_center':['LIKE',''],'docstatus':['!=',2]})
for idx,d in enumerate(query,start=0):
    doc = frappe.get_doc("Purchase Invoice",d.name)
    company_cost_center = frappe.db.get_value("Company",doc.company,'cost_center')
    doc.db_set('cost_center',company_cost_center,update_modified = False)
    if idx % 500 == 0:
        frappe.db.commit()
        print("commited at " + str(idx) + " " + str(d.name))
    print(str(idx) + " "+  str(d.name))