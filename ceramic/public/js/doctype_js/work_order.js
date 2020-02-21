frappe.ui.form.on('Work Order', {
	setup: function(frm){
        frm.set_query("production_item", function() {
			return {
				filters: {
					"item_group": frm.doc.item_group
				}
			}
        });
        frm.set_query("finish_item", function () {
            return {
                filters: {
                    "item_group": frm.doc.item_group,
                    "item_series": frm.doc.production_item
                }
            }
        });
	},
	item_group: function(frm){
        frappe.db.get_value('BOM', {'item_group': frm.doc.item_group,'is_active':1,'is_default':1 },'name',function (r) {
            if (r.name) {
                frm.set_value('bom_no',r.name)
            }
        })
    },
    source_warehouse: function (frm, cdt, cdn) {
        erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "required_items", "source_warehouse");
    },
    refresh: function (frm) {
        if (frm.doc.skip_transfer && frm.doc.docstatus == 1) {
            //frm.has_start_btn = true;
            if (frm.doc.status != "Completed") {
                var finish_btn = frm.add_custom_button(__('Work Order Finish'), function () {
                    frm.events.make_finish(frm);
                });
                finish_btn.addClass('btn-primary');
            }

            // let remaining_qty = flt(frm.doc.qty) - flt(frm.doc.manufacturing_start_qty);

            // if (remaining_qty > 0) {
            //     var start_btn = frm.add_custom_button(__('Start'), function () {
            //         frm.events.start_work_order(frm);
            //     });
            //     start_btn.addClass('btn-primary');
           // }
            frm.remove_custom_button('Finish');
            frm.remove_custom_button('Make Timesheet');
        }
    },
    make_finish: function (frm) {
        frappe.call({
            method: "ceramic.ceramic.doc_events.work_order.make_workorder_finish",
            args: {
                "work_order_id": frm.doc.name
            },
            callback: function (r) {
                var doclist = frappe.model.sync(r.message);
                frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
            }
        });
    },
    start_work_order: function (frm) {
        let max = flt(frm.doc.qty) - flt(frm.doc.manufacturing_start_qty);

        frappe.prompt({
            fieldtype: "Float", label: __("Qty to Start"), fieldname: "qty",
            description: __("Max: {0}", [max]), 'default': max
        }, function (data) {
            if (data.qty > max) {
                frappe.msgprint(__("Quantity must not be more than {0}", [max]));
                return;
            }
            frappe.ui.form.is_saving = true;

            frappe.call({
                method: "ceramic.doc_events.work_order.update_work_order_status",
                args: {
                    doc: frm.doc.name,
                    qty: data.qty
                },
                callback: function (r) {
                    cur_frm.refresh();
                },
                always: function () {
                    frappe.ui.form.is_saving = false;
                }
            });

            frm.reload_doc();

        }, __("Select Quantity"), __('Start'));
    },

    show_progress: function (frm) {
        var bars = [];
        var message = '';
        var added_min = false;

        // produced qty
        var title = __('{0} items produced', [frm.doc.produced_qty]);
        bars.push({
            'title': title,
            'width': (frm.doc.produced_qty / frm.doc.qty * 100) + '%',
            'progress_class': 'progress-bar-success'
        });
        if (bars[0].width == '0%') {
            bars[0].width = '0.5%';
            added_min = 0.5;
        }
        message = title;
        // pending qty
        if (frm.doc.skip_transfer && frm.doc.manufacturing_start_qty) {
            var pending_complete = frm.doc.manufacturing_start_qty - frm.doc.produced_qty;
            if (pending_complete) {
                var title = __('{0} items in progress', [pending_complete]);
                var width = ((pending_complete / frm.doc.qty * 100) - added_min);
                bars.push({
                    'title': title,
                    'width': (width > 100 ? "99.5" : width) + '%',
                    'progress_class': 'progress-bar-warning'
                })
                message = message + '. ' + title;
            }
        }
        let bar = cur_frm.dashboard.progress_area.find('div')[0];
        bar.hidden = true;

        let p = cur_frm.dashboard.progress_area.find('p')[0];
        p.hidden = true;
        frm.dashboard.add_progress(__('Status'), bars, message);
    },
});