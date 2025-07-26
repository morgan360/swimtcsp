module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
    './**/*.js',
    './**/*.py',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
}