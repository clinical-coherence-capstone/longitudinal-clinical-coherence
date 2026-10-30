const fs = require('fs');
const path = require('path');

const condData = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'DDX Plus', 'release_conditions.json'), 'utf8'));
const evidData = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'DDX Plus', 'release_evidences.json'), 'utf8'));

function decodeEvidenceToken(token) {
  let evidId = token;
  let valKey = null;

  if (token.includes('_@_')) {
    const parts = token.split('_@_');
    evidId = parts[0];
    valKey = parts[1];
  }

  const def = evidData[evidId];
  if (!def) {
    return { token, text: `[UNRESOLVED: ${token}]`, isAntecedent: false };
  }

  const q = def.question_en;
  let valText = '';

  if (valKey !== null) {
    if (def.value_meaning && def.value_meaning[valKey]) {
      valText = def.value_meaning[valKey].en || valKey;
    } else {
      valText = valKey; // Numeric scale like 0-10 or unmapped value
    }
  }

  let readable = '';
  if (def.data_type === 'B') {
    readable = `${q} -> YES`;
  } else if (def.data_type === 'C' || def.data_type === 'M') {
    readable = `${q} -> [Value: ${valText}]`;
  } else {
    readable = `${q} -> ${valText || 'YES'}`;
  }

  return {
    evidId,
    token,
    name: def.name,
    question: q,
    value: valText,
    readable,
    isAntecedent: def.is_antecedent,
    dataType: def.data_type
  };
}

function decodePatientRecord(record) {
  // Parse fields
  const age = record.AGE;
  const sex = record.SEX === 'M' ? 'Male' : record.SEX === 'F' ? 'Female' : record.SEX;
  const pathology = record.PATHOLOGY;
  const condInfo = condData[pathology] || { severity: 'Unknown', 'icd10-id': 'Unknown' };
  
  // Clean evidences string
  let rawEvids = [];
  try {
    rawEvids = JSON.parse(record.EVIDENCES.replace(/'/g, '"'));
  } catch (e) {
    rawEvids = record.EVIDENCES.replace(/[\[\]']/g, '').split(',').map(s => s.trim());
  }

  const initialEvid = record.INITIAL_EVIDENCE;
  const initialDecoded = decodeEvidenceToken(initialEvid);

  // Parse differential diagnosis
  let diffs = [];
  try {
    diffs = JSON.parse(record.DIFFERENTIAL_DIAGNOSIS.replace(/'/g, '"'));
  } catch (e) {
    diffs = [];
  }

  const symptoms = [];
  const antecedents = [];

  rawEvids.forEach(tok => {
    const dec = decodeEvidenceToken(tok);
    if (dec.isAntecedent) {
      antecedents.push(dec);
    } else {
      symptoms.push(dec);
    }
  });

  return {
    demographics: `${age}-year-old ${sex}`,
    chiefComplaint: initialDecoded.question,
    chiefComplaintToken: initialEvid,
    groundTruth: {
      pathology,
      icd10: condInfo['icd10-id'],
      severity: condInfo.severity
    },
    differentials: diffs.map(([name, prob]) => ({ name, prob: (prob * 100).toFixed(1) + '%' })),
    symptoms,
    antecedents
  };
}

// Test on sample row
const sampleRow = {
  AGE: 55,
  SEX: 'F',
  PATHOLOGY: 'Anemia',
  INITIAL_EVIDENCE: 'E_154',
  DIFFERENTIAL_DIAGNOSIS: "[['Anemia', 0.25071110167158567], ['Atrial fibrillation', 0.18612478078040334], ['Cluster headache', 0.11721971258749497], ['HIV (initial infection)', 0.11600212656027187], ['Anaphylaxis', 0.11338465680830324], ['Chagas', 0.10969575906379077], ['PSVT', 0.0784993666609853], ['Scombroid food poisoning', 0.028362495867164855]]",
  EVIDENCES: "['E_7', 'E_24', 'E_26', 'E_53', 'E_54_@_V_180', 'E_54_@_V_182', 'E_55_@_V_25', 'E_55_@_V_62', 'E_55_@_V_89', 'E_55_@_V_167', 'E_56_@_2', 'E_57_@_V_123', 'E_58_@_3', 'E_59_@_5', 'E_76', 'E_82', 'E_88', 'E_89', 'E_113', 'E_140', 'E_146', 'E_154', 'E_204_@_V_7', 'E_208']"
};

const decoded = decodePatientRecord(sampleRow);
console.log('=== CLINICAL CASE VIGNETTE ===');
console.log(`Patient: ${decoded.demographics}`);
console.log(`Chief Complaint: ${decoded.chiefComplaint} (Token: ${decoded.chiefComplaintToken})`);
console.log(`Ground Truth Pathology: ${decoded.groundTruth.pathology} (ICD-10: ${decoded.groundTruth.icd10}, Severity Tier: ${decoded.groundTruth.severity})`);

console.log('\n--- Differential Diagnosis Candidates ---');
decoded.differentials.forEach((d, i) => console.log(`  ${i+1}. ${d.name} (${d.prob})`));

console.log(`\n--- Acute Symptoms & Physical Exam Findings (${decoded.symptoms.length}) ---`);
decoded.symptoms.forEach(s => console.log(`  • ${s.readable}`));

console.log(`\n--- Antecedents & Medical History (${decoded.antecedents.length}) ---`);
decoded.antecedents.forEach(a => console.log(`  • ${a.readable}`));

module.exports = { decodeEvidenceToken, decodePatientRecord };
