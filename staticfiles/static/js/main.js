// Main JavaScript utility for Personal Expense Tracker

document.addEventListener('DOMContentLoaded', function () {
    // Auto-dismiss alert messages after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 6000);
    });

    // Form confirmation helper
    const deleteButtons = document.querySelectorAll('[data-confirm-delete]');
    deleteButtons.forEach(btn => {
        btn.addEventListener('click', function (e) {
            const item = this.getAttribute('data-confirm-delete') || 'this item';
            if (!confirm(`Are you sure you want to delete ${item}? This action cannot be undone.`)) {
                e.preventDefault();
            }
        });
    });
});
