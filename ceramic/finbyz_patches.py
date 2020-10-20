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

# Patch In GL Entry for Updating Cost Center in KC
data = frappe.get_list("GL Entry",{'company':'Koradiya Ceramics Pvt. Ltd.','cost_center':['LIKE','']})
print(len(data))
for idx,d in enumerate(data,start=0):
    frappe.db.set_value("GL Entry",d.name,'cost_center','Main - KC')
    if idx % 500 == 0:
        frappe.db.commit()
        print("committed " + str(idx) +  "  " + str(d.name))
    print(str(idx) +  "  " + str(d.name)) 