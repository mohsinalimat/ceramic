this.frm.cscript.onload = function (frm) {
    this.frm.set_query("primary_customer", "new_transaction_items", function (doc) {
        return { query: "erpnext.controllers.queries.customer_query" }
    });
}