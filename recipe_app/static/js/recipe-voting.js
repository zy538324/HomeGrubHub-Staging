/**
 * Positive Recipe Voting System
 * Prevents bullying by only allowing positive interactions
 */

class RecipeVoting {
    constructor() {
        this.bindEvents();
    }

    bindEvents() {
        document.addEventListener('click', (e) => {
            if (e.target.closest('.vote-btn')) {
                e.preventDefault();
                console.log('RecipeVoting: Vote button clicked');
                this.handleVote(e.target.closest('.vote-btn'));
            }
        });
    }

    async handleVote(button) {
        const recipeId = button.dataset.recipeId;
        const voteType = button.dataset.voteType;
        
        if (!recipeId || !voteType) {
            console.error('Missing recipe ID or vote type');
            return;
        }

        try {
            // Update button state immediately for better UX
            this.updateButtonState(button, 'loading');
            
            // Prepare form data with CSRF token
            const formData = new FormData();
            formData.append('recipe_id', recipeId);
            formData.append('vote_type', voteType);
            formData.append('csrf_token', this.getCSRFToken());
            
            console.log('RecipeVoting: Sending vote request', {
                recipe_id: recipeId,
                vote_type: voteType
            });
            
            const response = await fetch('/community/vote', {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: formData
            });

            console.log('RecipeVoting: Response status:', response.status);
            console.log('RecipeVoting: Response ok:', response.ok);

            const data = await response.json();
            console.log('RecipeVoting: Response data:', data);

            if (response.ok && data.success) {
                this.updateVoteDisplay(recipeId, data.vote_counts, data.user_vote);
                this.updateButtonState(button, 'success'); // Reset button state
                this.showToast('Vote recorded!', 'success');
            } else {
                console.error('Vote failed:', data);
                this.showToast(data.error || 'Failed to record vote', 'error');
                this.updateButtonState(button, 'error');
            }
        } catch (error) {
            console.error('Vote error:', error);
            this.showToast('Network error. Please try again.', 'error');
            this.updateButtonState(button, 'error');
        }
    }

    updateVoteDisplay(recipeId, voteCounts, userVote) {
        const container = document.querySelector(`[data-recipe-id="${recipeId}"]`)?.closest('.vote-container');
        if (!container) return;

        // Update vote counts with null checks
        const loveItCount = container.querySelector('.love-it-count');
        const wantToTryCount = container.querySelector('.want-to-try-count');
        const notFavoriteCount = container.querySelector('.not-favorite-count');
        const totalVotes = container.querySelector('.total-votes');

        if (loveItCount) loveItCount.textContent = voteCounts.love_it || 0;
        if (wantToTryCount) wantToTryCount.textContent = voteCounts.want_to_try || 0;
        if (notFavoriteCount) notFavoriteCount.textContent = voteCounts.not_favorite || 0;
        if (totalVotes) totalVotes.textContent = voteCounts.total || 0;

        // Update button states
        container.querySelectorAll('.vote-btn').forEach(btn => {
            btn.classList.remove('active', 'btn-primary', 'btn-success', 'btn-warning');
            btn.classList.add('btn-outline-secondary');
            
            if (btn.dataset.voteType === userVote) {
                btn.classList.remove('btn-outline-secondary');
                
                // Add appropriate color based on vote type
                switch (userVote) {
                    case 'love_it':
                        btn.classList.add('btn-success', 'active');
                        break;
                    case 'want_to_try':
                        btn.classList.add('btn-primary', 'active');
                        break;
                    case 'not_favorite':
                        btn.classList.add('btn-warning', 'active');
                        break;
                }
            }
        });
    }

    updateButtonState(button, state) {
        switch (state) {
            case 'loading':
                button.disabled = true;
                button.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Voting...';
                break;
            case 'success':
            case 'error':
            default:
                button.disabled = false;
                // Restore original button content from the template
                const voteType = button.dataset.voteType;
                let icon = '';
                let text = '';
                
                switch (voteType) {
                    case 'love_it':
                        icon = '<i class="fas fa-thumbs-up"></i>';
                        text = 'Love it!';
                        break;
                    case 'want_to_try':
                        icon = '<i class="fas fa-bookmark"></i>';
                        text = 'Want to try';
                        break;
                    case 'not_favorite':
                        icon = '<i class="fas fa-meh"></i>';
                        text = 'Not my favorite';
                        break;
                }
                
                const badgeClass = button.querySelector('span').className;
                const badgeText = button.querySelector('span').textContent;
                button.innerHTML = `${icon}<br><small>${text}</small><br><span class="${badgeClass}">${badgeText}</span>`;
                break;
        }
    }

    async loadVotes(recipeId) {
        try {
            const response = await fetch(`/community/recipe/${recipeId}/votes`);
            const data = await response.json();
            
            if (data.vote_counts) {
                this.updateVoteDisplay(recipeId, data.vote_counts, data.user_vote);
            }
        } catch (error) {
            console.error('Failed to load votes:', error);
        }
    }

    getCSRFToken() {
        // Try multiple methods to get CSRF token
        let token = '';
        
        // Method 1: Meta tag
        const metaToken = document.querySelector('meta[name="csrf-token"]');
        if (metaToken) {
            token = metaToken.getAttribute('content');
        }
        
        // Method 2: Hidden form field (Flask-WTF default)
        if (!token) {
            const hiddenToken = document.querySelector('input[name="csrf_token"]');
            if (hiddenToken) {
                token = hiddenToken.value;
            }
        }
        
        // Method 3: Try to get from any form on the page
        if (!token) {
            const anyForm = document.querySelector('form');
            if (anyForm) {
                const formToken = anyForm.querySelector('input[name="csrf_token"]');
                if (formToken) {
                    token = formToken.value;
                }
            }
        }
        
        console.log('CSRF Token found:', token ? 'Yes' : 'No');
        return token;
    }

    showToast(message, type = 'info') {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : 'success'} position-fixed`;
        toast.style.cssText = `
            top: 20px;
            right: 20px;
            z-index: 9999;
            min-width: 300px;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // Fade in
        setTimeout(() => {
            toast.style.opacity = '1';
        }, 100);
        
        // Auto remove
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if no other voting system is already handling this
    if (document.querySelector('.vote-container')?.dataset.handledByExternal) {
        console.log('Voting already handled by embedded script');
        return;
    }
    
    const voting = new RecipeVoting();
    
    // Mark as handled by external script
    const container = document.querySelector('.vote-container');
    if (container) {
        container.dataset.handledByExternal = 'true';
    }
    
    // Load existing votes for all recipes on the page
    const voteElements = document.querySelectorAll('.vote-container [data-recipe-id]');
    
    voteElements.forEach(element => {
        const recipeId = element.dataset.recipeId;
        if (recipeId) {
            voting.loadVotes(recipeId);
        }
    });
});

// Export for use in other modules
window.RecipeVoting = RecipeVoting;
