import { canonicalAtomId, canonicalAtomUrl } from './protocol/exact-link.js';

const A4 = { width: 595.28, height: 841.89 };
const MARGIN = 54;

function pdfEscape(value) {
  return String(value == null ? '' : value)
    .replace(/[^\x09\x0a\x0d\x20-\x7e]/g, '?')
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)')
    .replace(/\r?\n/g, '\\n');
}

function textLines(text, maxChars, maxLines) {
  const words = String(text || '').replace(/\s+/g, ' ').trim().split(' ').filter(Boolean);
  const lines = [];
  let line = '';
  for (const word of words) {
    const candidate = line ? `${line} ${word}` : word;
    if (candidate.length <= maxChars) {
      line = candidate;
      continue;
    }
    if (line) lines.push(line);
    line = word.length > maxChars ? word.slice(0, maxChars - 1) + '-' : word;
    if (lines.length >= maxLines) break;
  }
  if (line && lines.length < maxLines) lines.push(line);
  const truncated = words.join(' ').length > lines.join(' ').length;
  if (truncated && lines.length) lines[lines.length - 1] = lines[lines.length - 1].replace(/[.\s-]*$/, '') + '...';
  return { lines, truncated };
}

function qrMatrix(payload) {
  const qrFactory = globalThis.qrcode;
  if (typeof qrFactory !== 'function') throw new Error('QR generator is unavailable.');
  const qr = qrFactory(0, 'M');
  qr.addData(payload);
  qr.make();
  const count = qr.getModuleCount();
  const modules = [];
  for (let y = 0; y < count; y += 1) {
    for (let x = 0; x < count; x += 1) {
      if (qr.isDark(y, x)) modules.push([x, y]);
    }
  }
  return { count, modules };
}

function buildContent({ message, meta, url }) {
  const commands = [];
  const titleLines = textLines(message || 'Untitled Punkti', 39, 12);
  commands.push('0 0 0 rg');
  commands.push('/F1 11 Tf');
  commands.push(`1 0 0 1 ${MARGIN} ${A4.height - 62} Tm (${pdfEscape('Punkto')}) Tj`);
  commands.push('/F2 28 Tf');
  let y = A4.height - 116;
  for (const line of titleLines.lines) {
    commands.push(`1 0 0 1 ${MARGIN} ${y.toFixed(2)} Tm (${pdfEscape(line)}) Tj`);
    y -= 34;
  }
  if (titleLines.truncated) {
    commands.push('/F1 10 Tf');
    commands.push(`1 0 0 1 ${MARGIN} ${y.toFixed(2)} Tm (${pdfEscape('Message shortened for print. Open the link for the full Punkti.')}) Tj`);
    y -= 22;
  }

  commands.push('/F1 10 Tf');
  commands.push('0.35 0.35 0.35 rg');
  for (const line of textLines(meta, 76, 4).lines) {
    commands.push(`1 0 0 1 ${MARGIN} ${y.toFixed(2)} Tm (${pdfEscape(line)}) Tj`);
    y -= 15;
  }

  const qrSize = 250;
  const qrX = (A4.width - qrSize) / 2;
  const qrY = 144;
  commands.push('0 0 0 rg');
  commands.push(`${qrX - 12} ${qrY - 12} ${qrSize + 24} ${qrSize + 24} re S`);
  const matrix = qrMatrix(url);
  const moduleSize = qrSize / matrix.count;
  for (const [mx, my] of matrix.modules) {
    const x = qrX + mx * moduleSize;
    const rectY = qrY + (matrix.count - my - 1) * moduleSize;
    commands.push(`${x.toFixed(3)} ${rectY.toFixed(3)} ${Math.ceil(moduleSize * 1000) / 1000} ${Math.ceil(moduleSize * 1000) / 1000} re f`);
  }

  commands.push('/F1 9 Tf');
  commands.push('0 0 0 rg');
  let urlY = 92;
  for (const line of textLines(url, 82, 2).lines) {
    commands.push(`1 0 0 1 ${MARGIN} ${urlY} Tm (${pdfEscape(line)}) Tj`);
    urlY -= 12;
  }
  commands.push('/F1 8 Tf');
  commands.push('0.25 0.25 0.25 rg');
  commands.push(`1 0 0 1 ${MARGIN} ${36} Tm (${pdfEscape('punkto.xyz - leave a message here')}) Tj`);
  return commands.join('\n');
}

function makePdf(content) {
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${A4.width} ${A4.height}] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
  ];
  let pdf = '%PDF-1.4\n%\xE2\xE3\xCF\xD3\n';
  const offsets = [0];
  objects.forEach((obj, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${obj}\nendobj\n`;
  });
  const xrefAt = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (let i = 1; i < offsets.length; i += 1) {
    pdf += `${String(offsets[i]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefAt}\n%%EOF\n`;
  return new Uint8Array(Array.from(pdf, (char) => char.charCodeAt(0) & 0xff));
}

export async function qrPayloadForAtom(atom, origin = globalThis.location?.origin || '') {
  return canonicalAtomUrl(atom, origin);
}

export async function generatePunktiPdfBytes(atom, { origin = globalThis.location?.origin || '' } = {}) {
  const atomId = await canonicalAtomId(atom);
  const url = await canonicalAtomUrl(atomId, origin);
  const message = String(atom?.x || '').trim() || 'Untitled Punkti';
  const when = atom?.t ? new Date(Number(atom.t)).toISOString().replace('T', ' ').slice(0, 16) + ' UTC' : 'Date unavailable';
  const author = String(atom?.f || atom?.author || 'anonymous').trim();
  const place = String(atom?.punkto || '').trim();
  const meta = [when, place, author ? `author ${author}` : '', `atom ${atomId}`].filter(Boolean).join(' | ');
  return makePdf(buildContent({ message, meta, url }));
}

export async function downloadPunktiPdf(atom, opts = {}) {
  const bytes = await generatePunktiPdfBytes(atom, opts);
  const atomId = await canonicalAtomId(atom);
  const blob = new Blob([bytes], { type: 'application/pdf' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `punkto-punkti-${atomId.slice(0, 12)}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}
