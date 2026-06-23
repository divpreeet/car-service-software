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

    // Auto-calculate price from cost and margin
    document.getElementById('lineItemsContainer').addEventListener('input', function(e) {
        const el = e.target;
        if (el.classList.contains('line-cost') || el.classList.contains('line-margin')) {
            const row = el.closest('.line-item');
            const cost = parseFloat(row.querySelector('.line-cost').value) || 0;
            const margin = parseFloat(row.querySelector('.line-margin').value) || 0;
            if (cost > 0 && margin > 0) {
                const price = cost + (cost * margin / 100);
                row.querySelector('.line-price').value = price.toFixed(2);
            }
        }
    });
});

function addLineItem() {
    const container = document.getElementById('lineItemsContainer');
    const count = container.querySelectorAll('.line-item').length;
    
    const html = `
        <div class="line-item row mb-2">
            <div class="col-md-3">
                <input type="text" name="line_items[${count}][description]" class="form-control" placeholder="Description" required>
            </div>
            <div class="col-md-2">
                <select name="line_items[${count}][item_type]" class="form-select" required>
                    <option value="">-- Type --</option>
                    <option value="service">Service</option>
                    <option value="parts">Parts</option>
                    <option value="labor">Labor</option>
                    <option value="pickup_drop">Pickup-Drop</option>
                </select>
            </div>
            <div class="col-md-1">
                <select name="line_items[${count}][parts_type]" class="form-select">
                    <option value="">--</option>
                    <option value="original">Original</option>
                    <option value="aftermarket">Aftermarket</option>
                    <option value="used">Used</option>
                </select>
            </div>
            <div class="col-md-1">
                <select name="line_items[${count}][parts_source]" class="form-select" required>
                    <option value="">-- Source --</option>
                    <option value="workshop">Wrkshp</option>
                    <option value="ob">OB</option>
                </select>
            </div>
            <div class="col-md-1">
                <input type="number" name="line_items[${count}][cost]" class="form-control line-cost" placeholder="Cost" step="0.01">
            </div>
            <div class="col-md-1">
                <input type="number" name="line_items[${count}][margin]" class="form-control line-margin" placeholder="%" step="0.01" min="0">
            </div>
            <div class="col-md-1">
                <input type="number" name="line_items[${count}][quantity]" class="form-control" placeholder="Qty" value="1" step="0.01" required>
            </div>
            <div class="col-md-1">
                <input type="number" name="line_items[${count}][unit_price]" class="form-control line-price" placeholder="Price" step="0.01" required>
            </div>
            <div class="col-md-1">
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
