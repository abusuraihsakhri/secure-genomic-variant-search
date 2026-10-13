const { test } = require('node:test');
const assert = require('node:assert/strict');
const { parseVcf, searchVariants, csvEncode, DEMO_VCF } = require('../web/app.js');

test('parse VCF and search inclusive coordinates', () => {
  const rows = parseVcf(DEMO_VCF);
  assert.equal(rows.length, 4);
  assert.equal(searchVariants(rows, { chromosome: '7', start: '140453136', end: '140453136' }).length, 1);
  assert.equal(searchVariants(rows, { chromosome: 'chr1', text: 'DEMO1' }).length, 2);
});

test('reject invalid VCF files and out-of-range coordinates', () => {
  assert.throws(() => parseVcf('chr1\t1\t.\tA\tT\t.\tPASS\t.'), /header/);
  assert.throws(() => parseVcf('#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\nchr1\tNaN\t.\tA\tT\t.\tPASS\t.'), /Malformed/);
  assert.throws(() => searchVariants(parseVcf(DEMO_VCF), { start: '10', end: '9' }), /End coordinate/);
});

test('CSV output escapes quotes and neutralizes formula cells', () => {
  const row = { ...parseVcf(DEMO_VCF)[0], INFO: '=HYPERLINK("evil")' };
  const csv = csvEncode([row]);
  assert.match(csv, /"'=HYPERLINK\(""evil""\)"/);
  assert.match(csv, /"CHROM","POS"/);
});
