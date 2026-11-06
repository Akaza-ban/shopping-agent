// Kiểm tra chuỗi chưa bọc t() / msg() và chuỗi chưa dịch; dòng có i18n-ignore được bỏ qua.
import fs from 'node:fs';
import path from 'node:path';

const SRC = path.join(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..', 'src');
const VI = /[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]/i;
const CALL = /\b(?:t|msg|tr)\(\s*(['"`])((?:\\.|(?!\1)[^\\])*)\1/g;
// Chuỗi tiếng Việt cố ý giữ nguyên (tên ngôn ngữ hiển thị bằng chính ngôn ngữ đó)
const ALLOW = new Set(['Tiếng Việt']);

const files = [];
(function walk(dir) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    if (fs.statSync(p).isDirectory()) { if (name !== 'i18n') walk(p); }
    else if (/\.(ts|tsx)$/.test(name)) files.push(p);
  }
})(SRC);

const unwrapped = [];
const keys = new Map();
for (const file of files) {
  let inBlock = false;
  fs.readFileSync(file, 'utf8').split(/\r?\n/).forEach((raw, i) => {
    if (raw.includes('i18n-ignore')) return; // dòng cố ý giữ tiếng Việt (regex xử lý văn bản, lỗi cho lập trình viên)
    let line = raw;
    if (inBlock) {
      if (!line.includes('*/')) return;
      inBlock = false;
      line = line.slice(line.indexOf('*/') + 2);
    }
    line = line.replace(/\{\/\*.*?\*\/\}/g, '').replace(/\/\*.*?\*\//g, '');
    if (line.includes('/*')) { inBlock = true; line = line.slice(0, line.indexOf('/*')); }
    line = line.replace(/(^|[^:])\/\/.*$/, '$1');
    for (const m of line.matchAll(CALL)) {
      const key = m[2].replace(/\\(['"`\\])/g, '$1');
      if (!keys.has(key)) keys.set(key, `${path.relative(SRC, file)}:${i + 1}`);
    }
    let rest = line.replace(CALL, '');
    for (const a of ALLOW) rest = rest.split(a).join('');
    if (VI.test(rest)) unwrapped.push(`${path.relative(SRC, file)}:${i + 1}: ${raw.trim().slice(0, 140)}`);
  });
}

const enSource = fs.readFileSync(path.join(SRC, 'i18n', 'en.ts'), 'utf8');
const translated = new Set();
for (const m of enSource.matchAll(/^\s*(['"])((?:\\.|(?!\1)[^\\])*)\1\s*:/gm)) translated.add(m[2].replace(/\\(['"\\])/g, '$1'));
const missing = [...keys].filter(([k]) => VI.test(k) && !translated.has(k));

if (unwrapped.length) console.log(`Chuỗi tiếng Việt chưa bọc t()/msg() (${unwrapped.length}):\n  ` + unwrapped.join('\n  '));
if (missing.length) console.log(`Chưa có bản dịch tiếng Anh (${missing.length}):\n  ` + missing.map(([k, at]) => `${at}  ${JSON.stringify(k)}`).join('\n  '));
console.log(`Đã bọc ${keys.size} chuỗi, đã dịch ${translated.size}.`);
process.exit(unwrapped.length || missing.length ? 1 : 0);
