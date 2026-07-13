const fs = require('fs');
const path = require('path');

// Files changed in this session
const defaults = [
  'symptoms/womens-health/breast-health-tcm/index.html',
  'zh/symptoms/womens-health/breast-health-tcm/index.html',
  'symptoms/womens-health/index.html'
];

const files = process.argv.slice(2).length > 0
  ? process.argv.slice(2)
  : defaults.map(f => path.resolve(__dirname, f));

let ok = true;

files.forEach(f => {
  if (!fs.existsSync(f)) {
    console.log('SKIP ' + f + ': not found');
    return;
  }
  const c = fs.readFileSync(f, 'utf-8');
  const issues = [];
  if (!c.includes('<!DOCTYPE html>')) issues.push('missing DOCTYPE');
  if (!c.includes('</html>')) issues.push('missing </html>');
  if (!c.includes('</head>')) issues.push('missing </head>');
  if (!c.includes('</body>')) issues.push('missing </body>');
  if (c.includes('<!--TITLE-->')) issues.push('unreplaced TITLE');
  if (c.includes('<!--CONTENT-->')) issues.push('unreplaced CONTENT');
  if (c.includes('<!--H1-->')) issues.push('unreplaced H1');
  if (issues.length) { ok = false; console.log('FAIL ' + f + ': ' + issues.join(', ')); }
  else console.log('PASS ' + f);
});

process.exit(ok ? 0 : 1);
