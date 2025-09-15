document.addEventListener('DOMContentLoaded', () => {
    const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
    const container = document.getElementById('recipe-data');
    if (!container) return;

    const rateUrl = container.dataset.rateUrl;
    const commentUrl = container.dataset.commentUrl;

    document.querySelectorAll('.rate-star').forEach(star => {
        star.addEventListener('click', () => {
            const rating = star.dataset.value;
            fetch(rateUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ rating })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                }
            });
        });
    });

    const submitBtn = document.getElementById('submit-comment');
    if (submitBtn) {
        submitBtn.addEventListener('click', () => {
            const content = document.getElementById('new-comment').value.trim();
            if (!content) return;
            fetch(commentUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ content })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                }
            });
        });
    }

    document.querySelectorAll('.reply-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const parentId = btn.dataset.parent;
            const textarea = btn.previousElementSibling;
            const content = textarea.value.trim();
            if (!content) return;
            fetch(commentUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ content, parent_id: parentId })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    window.location.reload();
                }
            });
        });
    });
});
