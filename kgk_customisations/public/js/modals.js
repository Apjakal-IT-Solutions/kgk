frappe.ui.Dialog = class extends frappe.ui.Dialog {
    show() {
        super.show();
        // Fix aria-hidden after modal is shown
        setTimeout(() => {
            if (this.$wrapper && this.$wrapper.is(':visible')) {
                this.$wrapper.attr('aria-hidden', 'false');
            }
        }, 100);
    }
    
    hide() {
        if (this.$wrapper) {
            this.$wrapper.attr('aria-hidden', 'true');
        }
        super.hide();
    }
};