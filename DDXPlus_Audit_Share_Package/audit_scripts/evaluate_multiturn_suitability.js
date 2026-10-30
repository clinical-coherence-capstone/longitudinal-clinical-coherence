const fs = require('fs');
const path = require('path');
const { decodePatientRecord } = require('./case_decoder');

// Fixed random seed PRNG (simple Mulberry32)
function mulberry32(a) {
  return function() {
    var t = a += 0x6D2B79F5;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  }
}

const rng = mulberry32(20261027); // fixed seed

// Fast CSV row parser
function parseCsvLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === ',' && !inQuotes) {
      fields.push(current);
      current = '';
    } else {
      current += char;
    }
  }
  fields.push(current);
  return fields;
}

const valCsvPath = path.join(__dirname, '..', 'working_data', 'release_validate_patients.csv');
const lines = fs.readFileSync(valCsvPath, 'utf8').split('\n');

// Find sample cases for 3 clinical tiers:
// 1. Emergency (Severity 1): Possible NSTEMI / STEMI
// 2. Sub-acute (Severity 3): Pneumonia
// 3. Chronic/Ambulatory (Severity 4): Anemia
let caseNstemi = null;
let casePneumonia = null;
let caseAnemia = null;

for (let i = 1; i < lines.length; i++) {
  const l = lines[i].trim();
  if (!l) continue;
  const f = parseCsvLine(l);
  if (f.length < 6) continue;

  const row = {
    row_index: i,
    AGE: f[0],
    DIFFERENTIAL_DIAGNOSIS: f[1],
    SEX: f[2],
    PATHOLOGY: f[3],
    EVIDENCES: f[4],
    INITIAL_EVIDENCE: f[5]
  };

  if (!caseNstemi && row.PATHOLOGY === 'Possible NSTEMI / STEMI') caseNstemi = row;
  if (!casePneumonia && row.PATHOLOGY === 'Pneumonia') casePneumonia = row;
  if (!caseAnemia && row.PATHOLOGY === 'Anemia' && row.AGE === '55') caseAnemia = row;

  if (caseNstemi && casePneumonia && caseAnemia) break;
}

const sampled = [
  { label: 'Emergency (Severity 1)', row: caseNstemi },
  { label: 'Sub-acute (Severity 3)', row: casePneumonia },
  { label: 'Ambulatory (Severity 4)', row: caseAnemia }
];

console.log('Sampled cases for Multi-turn evaluation:');
sampled.forEach(s => {
  const dec = decodePatientRecord(s.row);
  console.log(`\n=== ${s.label}: ${dec.groundTruth.pathology} (Row ${s.row.row_index}) ===`);
  console.log(`Patient: ${dec.demographics} | Chief Complaint: ${dec.chiefComplaint}`);
  console.log(`Total symptoms: ${dec.symptoms.length} | Antecedents: ${dec.antecedents.length}`);
});
