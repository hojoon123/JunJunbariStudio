document.addEventListener('DOMContentLoaded', function() {
    const alertModal = new AlertModal("#alert-modal");

    document.querySelectorAll(".cart-button").forEach(function (button) {
        button.addEventListener("click", function (event) {
            event.preventDefault();
            const url = event.target.href;
            const data = {
                product_option: document.querySelector('#product-option').value,
                product_quantity: document.querySelector('#product-quantity').value
            };

            fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": window.csrf_token,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(data),
            }).then(function (response) {
                return response.status === 200 ? response.text() : Promise.reject(response);
            }).then(function () {
                alertModal.show("장바구니에 담았습니다.");
            }).catch(function (error) {
                alertModal.show("장바구니에 담기 실패했습니다.");
            });
        });
    });
});
