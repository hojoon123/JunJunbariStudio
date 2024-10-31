function AlertModal(css_selector) {
            const modal_ele = document.querySelector(css_selector);
            const modal = new bootstrap.Modal(modal_ele);
            this.show = function (message) {
                modal_ele.querySelector(".modal-body").textContent = message;
                modal.show();
            };
        }