frappe.listview_settings['Pick List'] = {
	get_indicator: function(doc) {
<<<<<<< HEAD
        if (doc.docstatus == 1){
            if (doc.per_delivered >= 99.99){
                return [__("Delivered"), "green", "status,=,Delivered"];
            }
            else{
                return [__("To Deliver"), "blue", "status,=,To Deliver"];
            }
        }
=======
		if (doc.docstatus == 1){
			if (doc.per_delivered >= 99.99){
				return [__("Delivered"), "green", "status,=,Delivered"];
			}
			else{
				return [__("To Deliver"), "blue", "status,=,To Deliver"];
			}
		}
>>>>>>> 0d26b3152bf13678f5cd22a8b67c749d2c44ffbb
	}
};
