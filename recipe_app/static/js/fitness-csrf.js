// Utility function to get CSRF token
function getCSRFToken() {
    // Try to get from hidden form field first
    const csrfInput = document.querySelector('[name=csrf_token]');
    if (csrfInput) {
        return csrfInput.value;
    }
    
    // Fallback to meta tag
    const csrfMeta = document.querySelector('meta[name=csrf-token]');
    if (csrfMeta) {
        return csrfMeta.getAttribute('content');
    }
    
    // Last resort - try to find it in any form
    const forms = document.querySelectorAll('form');
    for (let form of forms) {
        const token = form.querySelector('[name=csrf_token]');
        if (token) {
            return token.value;
        }
    }
    
    console.error('CSRF token not found');
    return null;
}

// Make fetch requests with CSRF token
function csrfFetch(url, options = {}) {
    const token = getCSRFToken();
    if (!token) {
        return Promise.reject(new Error('CSRF token not available'));
    }
    
    const headers = options.headers || {};
    headers['X-CSRFToken'] = token;
    
    return fetch(url, {
        ...options,
        headers: headers
    });
}
