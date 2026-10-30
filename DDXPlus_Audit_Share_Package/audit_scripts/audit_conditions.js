const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const filePath = path.join(__dirname, '..', 'DDX Plus', 'release_conditions.json');
const fileBuffer = fs.readFileSync(filePath);
const sha256 = crypto.createHash('sha256').update(fileBuffer).digest('hex');
console.log('SHA256 of release_conditions.json:', sha256);
console.log('Byte length:', fileBuffer.length);

const data = JSON.parse(fileBuffer.toString('utf8'));
const conditions = Object.keys(data);
console.log('Total conditions count:', conditions.length);

const icdMap = {};
const duplicateIcd = [];
const encodingIssues = [];

const rows = [
  'condition_id,condition_name_en,condition_name_fr,icd10_id,severity,symptom_count,antecedent_count,encoding_notes'
];

const conditionList = [];

conditions.forEach(key => {
  const item = data[key];
  const nameEn = item['cond-name-eng'] || key;
  const nameFr = item['cond-name-fr'] || '';
  const icd = (item['icd10-id'] || '').trim();
  const severity = item.severity;
  const symCount = item.symptoms ? Object.keys(item.symptoms).length : 0;
  const antCount = item.antecedents ? Object.keys(item.antecedents).length : 0;

  // Check ICD duplicate
  if (icdMap[icd]) {
    duplicateIcd.push({ icd, condition1: icdMap[icd], condition2: key });
  } else {
    icdMap[icd] = key;
  }

  // Check encoding issues
  let issues = [];
  if (nameFr.includes('Ac') || nameFr.includes("cA'") || nameFr.includes('A"') || nameFr.includes('A_') || nameFr.includes('\ufffd') || nameFr.includes('Ã')) {
    issues.push('French mojibake');
  }
  if (nameEn.includes('\ufffd') || nameEn.includes('Ã') || key.includes('\ufffd')) {
    issues.push('English mojibake');
  }

  if (issues.length > 0) {
    encodingIssues.push({ key, nameEn, nameFr, issues: issues.join('; ') });
  }

  conditionList.push({
    key,
    nameEn,
    nameFr,
    icd,
    severity,
    symCount,
    antCount,
    issues: issues.join('; ')
  });

  const escapeCsv = (str) => `"${String(str).replace(/"/g, '""')}"`;
  rows.push([
    escapeCsv(key),
    escapeCsv(nameEn),
    escapeCsv(nameFr),
    escapeCsv(icd),
    severity,
    symCount,
    antCount,
    escapeCsv(issues.join('; '))
  ].join(','));
});

const outputDir = path.join(__dirname, '..', 'audit_output');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

fs.writeFileSync(path.join(outputDir, 'condition_mapping_summary.csv'), rows.join('\n'), 'utf8');
console.log('Wrote condition_mapping_summary.csv');

// Print detailed stats
console.log('\n--- Duplicate ICD-10 codes ---');
console.log(JSON.stringify(duplicateIcd, null, 2));

console.log('\n--- Encoding issues ---');
console.log(`Found ${encodingIssues.length} condition(s) with encoding issues:`);
console.log(JSON.stringify(encodingIssues, null, 2));

console.log('\n--- Full Condition Table ---');
console.table(conditionList.map(c => ({
  Condition: c.key,
  ICD10: c.icd,
  Severity: c.severity,
  Symptoms: c.symCount,
  Antecedents: c.antCount
})));
