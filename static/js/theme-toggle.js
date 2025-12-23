/**
 * Theme Toggle Functionality
 * Handles dark/light mode switching with localStorage persistence
 */

(function() {
    'use strict';

    const THEME_KEY = 'warehouse-theme';
    const THEME_LIGHT = 'light';
    const THEME_DARK = 'dark';

    // Get the current theme from localStorage or default to light
    function getStoredTheme() {
        return localStorage.getItem(THEME_KEY) || THEME_LIGHT;
    }

    // Set the theme in localStorage
    function setStoredTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }

    // Apply theme to the document
    function applyTheme(theme) {
        const html = document.documentElement;
        html.setAttribute('data-theme', theme);
    }

    // Get the current theme
    function getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme') || THEME_LIGHT;
    }

    // Toggle between light and dark
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
        applyTheme(newTheme);
        setStoredTheme(newTheme);
        updateToggleButton(newTheme);
    }

    // Update the toggle button icon/text
    function updateToggleButton(theme) {
        const button = document.getElementById('themeToggle');
        if (button) {
            if (theme === THEME_DARK) {
                button.innerHTML = '☀️'; // Sun icon for light mode
                button.setAttribute('aria-label', 'Switch to light mode');
                button.title = 'Switch to light mode';
            } else {
                button.innerHTML = '🌙'; // Moon icon for dark mode
                button.setAttribute('aria-label', 'Switch to dark mode');
                button.title = 'Switch to dark mode';
            }
        }
    }

    // Initialize theme on page load
    function initTheme() {
        const storedTheme = getStoredTheme();
        applyTheme(storedTheme);
        updateToggleButton(storedTheme);
    }

    // Set up event listeners when DOM is ready
    function setupThemeToggle() {
        const button = document.getElementById('themeToggle');
        if (button) {
            button.addEventListener('click', toggleTheme);
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
            setupThemeToggle();
        });
    } else {
        // DOM is already ready
        initTheme();
        setupThemeToggle();
    }

    // Export for potential external use
    window.themeToggle = {
        toggle: toggleTheme,
        getCurrent: getCurrentTheme,
        set: function(theme) {
            if (theme === THEME_LIGHT || theme === THEME_DARK) {
                applyTheme(theme);
                setStoredTheme(theme);
                updateToggleButton(theme);
            }
        }
    };
})();

