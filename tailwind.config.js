/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './*/templates/**/*.html',   // Django app templates
    './templates/**/*.html',     // Project-level templates
    './**/*.html',              // Catch-all HTML files
    './static/js/**/*.js',      // JavaScript files
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
