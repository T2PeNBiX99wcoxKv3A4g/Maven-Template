// Theme Toggle and State Initialization
(function() {
    const themeBtn = document.getElementById('theme-btn');
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');

    function updateButtonState(theme) {
        if (!themeIcon || !themeText) return;
        if (theme === 'dark') {
            themeIcon.textContent = '☀️';
            themeText.textContent = 'Light';
        } else {
            themeIcon.textContent = '🌙';
            themeText.textContent = 'Dark';
        }
    }

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        localStorage.setItem('repo-theme', theme);
        updateButtonState(theme);
    }

    // Initialize button text based on current applied theme
    const currentTheme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    updateButtonState(currentTheme);

    if (themeBtn) {
        themeBtn.addEventListener('click', function() {
            document.body.classList.add('theme-transition');
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            applyTheme(isDark ? 'light' : 'dark');
            setTimeout(function() {
                document.body.classList.remove('theme-transition');
            }, 300);
        });
    }
})();

// Filter Functionality
(function() {
    const filterInput = document.getElementById('filter-input');
    const rows = document.querySelectorAll('.entry-row');
    if (!filterInput) return;

    filterInput.addEventListener('input', function() {
        const query = this.value.trim().toLowerCase();
        let visibleCount = 0;

        rows.forEach(function(row) {
            const name = row.getAttribute('data-name');
            if (!query || name.indexOf(query) !== -1) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });
    });
})();

// Snippet Tab Switching & Clipboard
let activeSnippetType = 'maven';

function switchSnippet(type, element) {
    activeSnippetType = type;
    const container = element ? element.closest('.snippet-card') : document;
    const tabs = (container || document).querySelectorAll('.snippet-tab');
    
    tabs.forEach(function(tab) {
        if (element && tab === element) {
            tab.classList.add('active');
        } else if (!element && tab.getAttribute('data-type') === type) {
            tab.classList.add('active');
        } else {
            tab.classList.remove('active');
        }
    });

    const mavenBox = document.getElementById('snippet-maven');
    const gradleBox = document.getElementById('snippet-gradle');
    const kotlinBox = document.getElementById('snippet-kotlin');

    if (mavenBox) mavenBox.style.display = type === 'maven' ? 'block' : 'none';
    if (gradleBox) gradleBox.style.display = type === 'gradle' ? 'block' : 'none';
    if (kotlinBox) kotlinBox.style.display = type === 'kotlin' ? 'block' : 'none';
}

// Global exposure
window.switchSnippet = switchSnippet;

// Copy Snippet
function copySnippet() {
    const targetBox = document.getElementById('snippet-' + activeSnippetType) || 
                      document.querySelector('.snippet-code[style*="block"]') || 
                      document.getElementById('snippet-maven');
    if (targetBox) {
        navigator.clipboard.writeText(targetBox.textContent.trim()).then(function() {
            const btn = document.querySelector('.copy-btn');
            if (btn) {
                const old = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(function() { btn.textContent = old; }, 1500);
            }
        });
    }
}

window.copySnippet = copySnippet;
