/** @type {import('tailwindcss').Config} */
module.exports = {
  // Tailwind only emits the classes it finds here. Anything used but not scanned
  // is silently absent from the built stylesheet — no error, just an unstyled
  // element — so this list needs to cover every place a class name can appear.
  content: [
    './*/templates/**/*.html',   // Django app templates
    './templates/**/*.html',     // Project-level templates
    './**/*.html',              // Catch-all HTML files
    './static/js/**/*.js',      // JavaScript files
    // static/chatbot/chat.js builds the chat bubbles in JavaScript, so its class
    // names live nowhere else. They only survived earlier builds because the same
    // classes happened to appear in a template too. Named specifically rather
    // than './static/**/*.js', which also sweeps vendored DataTables and Django
    // admin scripts and invents classes from words inside their strings.
    './static/chatbot/**/*.js',
  ],
  // Known gap, deliberately not scanned: a couple of views build small HTML
  // fragments in Python (finances/views.py). Adding './**/*.py' would walk .venv
  // on every build. Those fragments use only common classes; if that changes,
  // add the file here rather than the whole tree.
  theme: {
    extend: {},
  },
  plugins: [],
};
