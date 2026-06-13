// Car Service Software JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Dynamic line items
    const addLineItemBtn = document.getElementById('addLineItem');
    if (addLineItemBtn) {
        addLineItemBtn.addEventListener('click', function() {
            addLineItem();
        });
    }
});

function addLineItem() {
    const container = document.getElementById('lineItemsContainer');
    const count = container.querySelectorAll('.line-item').length;
    
    const html = `
        <div class="line-item row mb-2">
            <div class="col-md-4">
                <input type="text" name="line_items[${count}][description]" class="form-control" placeholder="Description">
            </div>
            <div class="col-md-2">
                <select name="line_items[${count}][item_type]" class="form-select">
                    <option value="service">Service</option>
                    <option value="parts">Parts</option>
                    <option value="labor">Labor</option>
                </select>
            </div>
            <div class="col-md-2">
                <input type="number" name="line_items[${count}][quantity]" class="form-control" placeholder="Qty" value="1" step="0.01">
            </div>
            <div class="col-md-2">
                <input type="number" name="line_items[${count}][unit_price]" class="form-control" placeholder="Price" step="0.01">
            </div>
            <div class="col-md-2">
                <button type="button" class="btn btn-danger btn-sm" onclick="removeLineItem(this)">Remove</button>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', html);
    updateLineItemsCount();
}

function removeLineItem(btn) {
    btn.closest('.line-item').remove();
    updateLineItemsCount();
}

function updateLineItemsCount() {
    const container = document.getElementById('lineItemsContainer');
    const count = container.querySelectorAll('.line-item').length;
    document.getElementById('lineItemsCount').value = count;
}

function calculateTotal() {
    // Auto-calculate totals if needed
    const subtotalField = document.getElementById('subtotal');
    const taxField = document.getElementById('tax');
    const totalField = document.getElementById('total');
    
    if (subtotalField && taxField && totalField) {
        const subtotal = parseFloat(subtotalField.value || 0);
        const tax = subtotal * (parseFloat(taxField.value || 0.1));
        const total = subtotal + tax;
        totalField.value = total.toFixed(2);
    }
}
