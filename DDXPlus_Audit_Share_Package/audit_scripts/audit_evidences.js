const fs = require('fs');
const crypto = require('crypto');
const path = require('path');

const filePath = path.join(__dirname, '..', 'DDX Plus', 'release_evidences.json');
const fileBuffer = fs.readFileSync(filePath);
const sha256 = crypto.createHash('sha256').update(fileBuffer).digest('hex');
console.log('SHA256 of release_evidences.json:', sha256);
console.log('Byte length:', fileBuffer.length);

const data = JSON.parse(fileBuffer.toString('utf8'));
const keys = Object.keys(data);
console.log('Total evidence keys:', keys.length);

// Analyze data types, antecedents vs symptoms, default values, value mappings
const dataTypes = {};
let antecedentsCount = 0;
let symptomsCount = 0;
const missingFields = [];
const valueTypes = {};
const evidenceList = [];

// For CSV output
const rows = [
  'evidence_id,name,data_type,is_antecedent,default_value,question_en,question_fr,possible_values_count,value_meanings_count,sample_values'
];

keys.forEach(k => {
  const item = data[k];
  const dt = item.data_type || 'UNKNOWN';
  dataTypes[dt] = (dataTypes[dt] || 0) + 1;
  
  if (item.is_antecedent) {
    antecedentsCount++;
  } else {
    symptomsCount++;
  }

  // Check required fields
  if (!item.name || item.data_type === undefined || item.is_antecedent === undefined) {
    missingFields.push({ key: k, item });
  }

  const possibleVals = item['possible-values'] || [];
  const valMeanings = item.value_meaning || {};
  const valMeaningKeys = Object.keys(valMeanings);

  // Sample values representation
  let sampleVals = [];
  if (valMeaningKeys.length > 0) {
    sampleVals = valMeaningKeys.slice(0, 3).map(vk => {
      const en = valMeanings[vk]?.en || vk;
      return `${vk}: ${en}`;
    });
  } else if (possibleVals.length > 0) {
    sampleVals = possibleVals.slice(0, 3).map(String);
  }

  const escapeCsv = (str) => `"${String(str || '').replace(/"/g, '""')}"`;
  rows.push([
    escapeCsv(k),
    escapeCsv(item.name),
    escapeCsv(dt),
    item.is_antecedent,
    escapeCsv(item.default_value),
    escapeCsv(item.question_en),
    escapeCsv(item.question_fr),
    possibleVals.length,
    valMeaningKeys.length,
    escapeCsv(sampleVals.join('; '))
  ].join(','));

  evidenceList.push({
    id: k,
    name: item.name,
    type: dt,
    is_antecedent: item.is_antecedent,
    default_val: item.default_value,
    q_en: item.question_en,
    val_count: valMeaningKeys.length || possibleVals.length
  });
});

console.log('\n--- Data Type Distribution ---');
console.log(JSON.stringify(dataTypes, null, 2));

console.log('\n--- Category Distribution ---');
console.log(`Antecedents (Medical History / Risk factors): ${antecedentsCount}`);
console.log(`Symptoms / Physical Findings: ${symptomsCount}`);
console.log(`Missing required fields: ${missingFields.length}`);

// Check ID range / gaps
const numericIds = keys.map(k => {
  const match = k.match(/^E_(\d+)$/);
  return match ? parseInt(match[1], 10) : null;
}).filter(n => n !== null).sort((a, b) => a - b);

console.log(`\nNumeric ID range: min=${numericIds[0]}, max=${numericIds[numericIds.length - 1]}`);
const allExpected = [];
for (let i = numericIds[0]; i <= numericIds[numericIds.length - 1]; i++) {
  if (!numericIds.includes(i)) allExpected.push(`E_${i}`);
}
console.log(`Missing / Gapped IDs in sequence (${allExpected.length}):`, allExpected);

// Save CSV
const outputDir = path.join(__dirname, '..', 'audit_output');
fs.writeFileSync(path.join(outputDir, 'evidence_mapping_summary.csv'), rows.join('\n'), 'utf8');
console.log('\nWrote evidence_mapping_summary.csv');
