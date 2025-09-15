    let cookieBanner = null;
    let cookieModal = null;
    
    window.addEventListener('load', function() {
      if (!localStorage.getItem('cookieConsent')) {
        createCookieBanner();
        createCookieModal();
      }
    });

    function createCookieBanner() {
      cookieBanner = document.createElement('div');
      cookieBanner.id = 'cookie-consent-banner';
      cookieBanner.innerHTML = `
        <div style="position: fixed; bottom: 0; left: 0; right: 0; background: #2c3e50; color: white; padding: 15px; z-index: 9999; font-family: Arial, sans-serif; box-shadow: 0 -2px 10px rgba(0,0,0,0.1);">
          <div style="max-width: 1200px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;">
            <div style="flex: 1; margin-right: 20px; min-width: 300px;">
              <strong>🍪 We use cookies to improve your experience</strong><br>
              <small>We use cookies for essential functionality and analytics. Click 'Customise' to see what cookies we use and manage your preferences.</small>
            </div>
            <div style="display: flex; gap: 10px; flex-wrap: wrap;">
              <button id="accept-all-cookies-btn" style="background: #27ae60; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background-color 0.3s ease;">Accept All</button>
              <button id="reject-all-cookies-btn" style="background: #e74c3c; color: white; border: none; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background-color 0.3s ease;">Reject All</button>
              <button id="customise-cookies-btn" style="background: transparent; color: white; border: 1px solid white; padding: 10px 18px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: all 0.3s ease;">Customise</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(cookieBanner);
      
      // Add event listeners to buttons
      document.getElementById('accept-all-cookies-btn').addEventListener('click', acceptAllCookies);
      document.getElementById('reject-all-cookies-btn').addEventListener('click', rejectAllCookies);
      document.getElementById('customise-cookies-btn').addEventListener('click', showCookieModal);
      
      // Add hover effects
      const acceptBtn = document.getElementById('accept-all-cookies-btn');
      const rejectBtn = document.getElementById('reject-all-cookies-btn');
      const customiseBtn = document.getElementById('customise-cookies-btn');
      
      acceptBtn.addEventListener('mouseenter', function() {
        this.style.backgroundColor = '#229954';
      });
      acceptBtn.addEventListener('mouseleave', function() {
        this.style.backgroundColor = '#27ae60';
      });
      
      rejectBtn.addEventListener('mouseenter', function() {
        this.style.backgroundColor = '#c0392b';
      });
      rejectBtn.addEventListener('mouseleave', function() {
        this.style.backgroundColor = '#e74c3c';
      });
      
      customiseBtn.addEventListener('mouseenter', function() {
        this.style.backgroundColor = 'rgba(255,255,255,0.1)';
      });
      customiseBtn.addEventListener('mouseleave', function() {
        this.style.backgroundColor = 'transparent';
      });
    }

    function createCookieModal() {
      cookieModal = document.createElement('div');
      cookieModal.id = 'cookie-modal';
      cookieModal.style.display = 'none';
      cookieModal.innerHTML = `
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); z-index: 10000; display: flex; align-items: center; justify-content: center; padding: 20px; font-family: Arial, sans-serif;">
          <div style="background: white; border-radius: 12px; max-width: 600px; max-height: 90vh; overflow-y: auto; width: 100%;">
            <div style="padding: 25px; border-bottom: 1px solid #eee;">
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: #2c3e50;">Cookie Settings</h3>
                <button id="close-modal-btn" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #999; line-height: 1;">&times;</button>
              </div>
            </div>
            <div style="padding: 25px;">
              <p style="margin: 0 0 20px 0; color: #555;">We use cookies to enhance your experience on Home Grub Hub. Below are the types of cookies we use and their purposes under UK law:</p>
              
              <div style="margin-bottom: 25px; border: 1px solid #e3e3e3; border-radius: 8px; padding: 20px;">
                <h4 style="margin: 0 0 15px 0; color: #2c3e50; display: flex; align-items: center; justify-content: space-between;">
                  <span>🔒 Essential Cookies</span>
                  <span style="font-size: 12px; background: #e74c3c; color: white; padding: 3px 8px; border-radius: 12px; font-weight: normal;">Required</span>
                </h4>
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">These cookies are necessary for the website to function properly. They cannot be disabled.</p>
                <ul style="margin: 0; padding-left: 20px; color: #666; font-size: 14px;">
                  <li>Session management and user authentication</li>
                  <li>Security and fraud prevention</li>
                  <li>Shopping basket functionality</li>
                  <li>Form data retention during browsing</li>
                </ul>
              </div>
              
              <div style="margin-bottom: 25px; border: 1px solid #e3e3e3; border-radius: 8px; padding: 20px;">
                <h4 style="margin: 0 0 15px 0; color: #2c3e50; display: flex; align-items: center; justify-content: space-between;">
                  <span>📊 Analytics Cookies</span>
                  <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="analytics-cookies" style="margin-right: 8px;">
                    <span style="font-size: 12px; font-weight: normal;">Enable</span>
                  </label>
                </h4>
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">Help us understand how you use our website to improve your experience.</p>
                <ul style="margin: 0; padding-left: 20px; color: #666; font-size: 14px;">
                  <li><strong>Google Analytics:</strong> Page views, user journeys, popular content</li>
                  <li><strong>Microsoft Clarity:</strong> User session recordings and heatmaps</li>
                  <li>Site performance monitoring and error tracking</li>
                  <li>Understanding user preferences and behaviour</li>
                </ul>
              </div>
              
              <div style="margin-bottom: 25px; border: 1px solid #e3e3e3; border-radius: 8px; padding: 20px;">
                <h4 style="margin: 0 0 15px 0; color: #2c3e50; display: flex; align-items: center; justify-content: space-between;">
                  <span>⚙️ Functional Cookies</span>
                  <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="functional-cookies" style="margin-right: 8px;">
                    <span style="font-size: 12px; font-weight: normal;">Enable</span>
                  </label>
                </h4>
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">Remember your preferences to personalise your experience.</p>
                <ul style="margin: 0; padding-left: 20px; color: #666; font-size: 14px;">
                  <li>Remembering your meal planning preferences</li>
                  <li>Storing your dietary requirements and restrictions</li>
                  <li>Language and region preferences</li>
                  <li>Theme and display settings</li>
                </ul>
              </div>
              
              <div style="margin-bottom: 25px; border: 1px solid #e3e3e3; border-radius: 8px; padding: 20px;">
                <h4 style="margin: 0 0 15px 0; color: #2c3e50; display: flex; align-items: center; justify-content: space-between;">
                  <span>🎯 Marketing Cookies</span>
                  <label style="display: flex; align-items: center; cursor: pointer;">
                    <input type="checkbox" id="marketing-cookies" style="margin-right: 8px;">
                    <span style="font-size: 12px; font-weight: normal;">Enable</span>
                  </label>
                </h4>
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">Used to show you relevant content and advertisements.</p>
                <ul style="margin: 0; padding-left: 20px; color: #666; font-size: 14px;">
                  <li>Personalised recipe recommendations</li>
                  <li>Relevant promotional content</li>
                  <li>Social media integration features</li>
                  <li>Third-party advertising partnerships</li>
                </ul>
              </div>
              
              <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                <h5 style="margin: 0 0 10px 0; color: #2c3e50;">Your Rights Under UK Law</h5>
                <p style="margin: 0; font-size: 14px; color: #666;">
                  Under UK GDPR and PECR regulations, you have the right to control how cookies are used on your device. 
                  You can change these settings at any time by accessing this panel again through our 
                  <a href="{{ url_for('main.cookie_policy') }}" target="_blank" style="color: #007bff;">Cookie Policy</a> page.
                </p>
              </div>
            </div>
            <div style="padding: 20px 25px; border-top: 1px solid #eee; display: flex; gap: 10px; justify-content: flex-end;">
              <button id="save-preferences-btn" style="background: #27ae60; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background-color 0.3s ease;">Save Preferences</button>
              <button id="accept-all-modal-btn" style="background: #007bff; color: white; border: none; padding: 12px 24px; border-radius: 6px; cursor: pointer; font-weight: 500; transition: background-color 0.3s ease;">Accept All</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(cookieModal);
      
      // Add event listeners for modal
      document.getElementById('close-modal-btn').addEventListener('click', hideCookieModal);
      document.getElementById('save-preferences-btn').addEventListener('click', saveCustomPreferences);
      document.getElementById('accept-all-modal-btn').addEventListener('click', acceptAllFromModal);
      
      // Close modal when clicking outside
      cookieModal.addEventListener('click', function(e) {
        if (e.target === cookieModal) {
          hideCookieModal();
        }
      });
      
      // Set default preferences
      document.getElementById('analytics-cookies').checked = true;
      document.getElementById('functional-cookies').checked = true;
      document.getElementById('marketing-cookies').checked = false;
    }

    function showCookieModal() {
      cookieModal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }
    
    function hideCookieModal() {
      cookieModal.style.display = 'none';
      document.body.style.overflow = 'auto';
    }

    function acceptAllCookies() {
      const preferences = {
        essential: true,
        analytics: true,
        functional: true,
        marketing: true
      };
      saveCookiePreferences('accepted', preferences);
      removeCookieBanner();
    }

    function rejectAllCookies() {
      const preferences = {
        essential: true, // Essential cookies cannot be disabled
        analytics: false,
        functional: false,
        marketing: false
      };
      saveCookiePreferences('declined', preferences);
      removeCookieBanner();
    }
    
    function acceptAllFromModal() {
      document.getElementById('analytics-cookies').checked = true;
      document.getElementById('functional-cookies').checked = true;
      document.getElementById('marketing-cookies').checked = true;
      saveCustomPreferences();
    }
    
    function saveCustomPreferences() {
      const preferences = {
        essential: true, // Always true
        analytics: document.getElementById('analytics-cookies').checked,
        functional: document.getElementById('functional-cookies').checked,
        marketing: document.getElementById('marketing-cookies').checked
      };
      
      const consentStatus = (preferences.analytics || preferences.functional || preferences.marketing) ? 'custom' : 'minimal';
      saveCookiePreferences(consentStatus, preferences);
      hideCookieModal();
      removeCookieBanner();
    }
    
    function saveCookiePreferences(status, preferences) {
      localStorage.setItem('cookieConsent', status);
      localStorage.setItem('cookieConsentDate', new Date().toISOString());
      localStorage.setItem('cookiePreferences', JSON.stringify(preferences));
      
      // Update Google Analytics consent if gtag is available
      if (typeof gtag !== 'undefined') {
        gtag('consent', 'update', {
          'analytics_storage': preferences.analytics ? 'granted' : 'denied',
          'ad_storage': preferences.marketing ? 'granted' : 'denied',
          'functionality_storage': preferences.functional ? 'granted' : 'denied'
        });
      }
      
      // Apply preferences immediately
      applyCookiePreferences(preferences);
    }
    
    function applyCookiePreferences(preferences) {
      // Handle analytics cookies
      if (!preferences.analytics) {
        // Disable analytics tracking
        if (typeof gtag !== 'undefined') {
          gtag('config', 'GA_MEASUREMENT_ID', { 'anonymize_ip': true, 'storage': 'none' });
        }
        // Clear existing analytics cookies
        deleteCookiesByPattern('_ga');
        deleteCookiesByPattern('_gid');
        deleteCookiesByPattern('_gat');
      }
      
      // Handle Microsoft Clarity
      if (!preferences.analytics && typeof clarity !== 'undefined') {
        try {
          clarity('consent', false);
        } catch(e) {
          console.log('Could not disable Microsoft Clarity');
        }
      }
      
      // Handle functional cookies
      if (!preferences.functional) {
        // Clear functional cookies but keep essential ones
        deleteCookiesByPattern('user_preferences');
        deleteCookiesByPattern('theme');
      }
      
      // Handle marketing cookies
      if (!preferences.marketing) {
        // Clear marketing cookies
        deleteCookiesByPattern('marketing');
        deleteCookiesByPattern('ads');
      }
    }
    
    function deleteCookiesByPattern(pattern) {
      const cookies = document.cookie.split(";");
      for (let cookie of cookies) {
        const eqPos = cookie.indexOf("=");
        const name = eqPos > -1 ? cookie.substr(0, eqPos).trim() : cookie.trim();
        if (name.includes(pattern)) {
          document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;domain=" + window.location.hostname;
          document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/";
        }
      }
    }

    function acceptCookies() {
      localStorage.setItem('cookieConsent', 'accepted');
      localStorage.setItem('cookieConsentDate', new Date().toISOString());
      
      // Update Google Analytics consent if gtag is available
      if (typeof gtag !== 'undefined') {
        gtag('consent', 'update', {
          'analytics_storage': 'granted'
        });
      }
      
      removeCookieBanner();
    }

    function rejectCookies() {
      localStorage.setItem('cookieConsent', 'declined');
      localStorage.setItem('cookieConsentDate', new Date().toISOString());
      
      // Update Google Analytics consent if gtag is available
      if (typeof gtag !== 'undefined') {
        gtag('consent', 'update', {
          'analytics_storage': 'denied'
        });
      }
      
      removeCookieBanner();
    }
    
    function removeCookieBanner() {
      if (cookieBanner && cookieBanner.parentNode) {
        // Add fade out animation
        cookieBanner.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
        cookieBanner.style.opacity = '0';
        cookieBanner.style.transform = 'translateY(100%)';
        
        // Remove element after animation
        setTimeout(function() {
          if (cookieBanner && cookieBanner.parentNode) {
            cookieBanner.parentNode.removeChild(cookieBanner);
          }
          cookieBanner = null;
        }, 300);
      }
    }
    
    // Global function to reopen cookie settings
    function reopenCookieSettings() {
      // Check if user has already made cookie choices
      const hasConsent = localStorage.getItem('cookieConsent');
      
      if (hasConsent) {
        // If they have existing preferences, load and show the modal directly
        if (typeof createCookieModal === 'function' && typeof showCookieModal === 'function') {
          // Create modal if it doesn't exist
          if (!cookieModal || !document.getElementById('cookie-modal')) {
            createCookieModal();
          }
          
          // Load existing preferences into the modal
          const preferences = JSON.parse(localStorage.getItem('cookiePreferences') || '{}');
          if (document.getElementById('analytics-cookies')) {
            document.getElementById('analytics-cookies').checked = preferences.analytics || false;
          }
          if (document.getElementById('functional-cookies')) {
            document.getElementById('functional-cookies').checked = preferences.functional || false;
          }
          if (document.getElementById('marketing-cookies')) {
            document.getElementById('marketing-cookies').checked = preferences.marketing || false;
          }
          
          showCookieModal();
        } else {
          alert('Cookie settings are not available on this page. Please visit the Cookie Policy page.');
        }
      } else {
        // If no consent yet, create banner and modal
        if (typeof createCookieBanner === 'function' && typeof createCookieModal === 'function') {
          createCookieBanner();
          createCookieModal();
          showCookieModal();
        } else {
          alert('Cookie settings will appear after page reload.');
          window.location.reload();
        }
      }
    }
