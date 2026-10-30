const fs = require('fs');
const readline = require('readline');
const crypto = require('crypto');
const path = require('path');

// Load knowledge bases
const condPath = path.join(__dirname, '..', 'DDX Plus', 'release_conditions.json');
const evidPath = path.join(__dirname, '..', 'DDX Plus', 'release_evidences.json');
const condData = JSON.parse(fs.readFileSync(condPath, 'utf8'));
const evidData = JSON.parse(fs.readFileSync(evidPath, 'utf8'));
const validCondKeys = new Set(Object.keys(condData));
const validEvidKeys = new Set(Object.keys(evidData));

const csvPath = path.join(__dirname, '..', 'working_data', 'release_validate_patients.csv');

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

// Compute SHA256 of extracted CSV
console.log('Calculating SHA-256 of release_validate_patients.csv...');
const fileBuf = fs.readFileSync(csvPath);
const sha256 = crypto.createHash('sha256').update(fileBuf).digest('hex');
console.log('Extracted file SHA-256:', sha256);
console.log('Extracted file size (bytes):', fileBuf.length);

const rl = readline.createInterface({
  input: fs.createReadStream(csvPath),
  crlfDelay: Infinity
});

let totalRecords = 0;
let headerSeen = false;

// Statistics accumulators
const sexCounts = { M: 0, F: 0, other: 0 };
const ages = [];
const conditionCounts = {};
const initialEvidCounts = {};
const evidenceCountsPerCase = [];
const diffDiagnosisCounts = [];

// Validation checks
let missingAge = 0;
let invalidAge = 0;
let missingSex = 0;
let invalidSex = 0;
let missingPathology = 0;
let unknownPathology = 0;
let missingEvidences = 0;
let missingInitialEvid = 0;
let initialEvidNotInEvidences = 0;
let missingDifferential = 0;

// Token resolution
const unresolvedTokens = new Set();
let totalTokenEvaluations = 0;

// Differential diagnosis accuracy stats
let pathologyInDiffCount = 0;
let pathologyTop1Count = 0;
let pathologyTop3Count = 0;
let pathologyProbSum = 0;

// Duplicates tracking
const caseHashMap = new Map(); // hash -> count
let exactDuplicateRows = 0;

console.log('Streaming and auditing records...');
const startTime = Date.now();

rl.on('line', (line) => {
  if (!headerSeen) {
    headerSeen = true;
    return; // skip header: AGE,DIFFERENTIAL_DIAGNOSIS,SEX,PATHOLOGY,EVIDENCES,INITIAL_EVIDENCE
  }

  totalRecords++;
  const fields = parseCsvLine(line);
  if (fields.length < 6) {
    console.error(`Malformed row at record ${totalRecords}: length ${fields.length}`);
    return;
  }

  const rawAge = fields[0];
  const rawDiff = fields[1];
  const rawSex = fields[2];
  const rawPathology = fields[3];
  const rawEvidences = fields[4];
  const rawInitialEvid = fields[5];

  // 1. Age
  const age = parseInt(rawAge, 10);
  if (isNaN(age)) {
    missingAge++;
  } else {
    if (age < 0 || age > 130) invalidAge++;
    ages.push(age);
  }

  // 2. Sex
  if (rawSex === 'M' || rawSex === 'F') {
    sexCounts[rawSex]++;
  } else {
    if (!rawSex) missingSex++;
    else invalidSex++;
    sexCounts.other++;
  }

  // 3. Pathology
  if (!rawPathology) {
    missingPathology++;
  } else {
    if (!validCondKeys.has(rawPathology)) {
      unknownPathology++;
    }
    conditionCounts[rawPathology] = (conditionCounts[rawPathology] || 0) + 1;
  }

  // 4. Initial Evidence
  if (!rawInitialEvid) {
    missingInitialEvid++;
  } else {
    initialEvidCounts[rawInitialEvid] = (initialEvidCounts[rawInitialEvid] || 0) + 1;
  }

  // 5. Evidences parsing
  let evidencesList = [];
  try {
    evidencesList = JSON.parse(rawEvidences.replace(/'/g, '"'));
  } catch (e) {
    evidencesList = rawEvidences.replace(/[\[\]']/g, '').split(',').map(s => s.trim()).filter(Boolean);
  }

  if (evidencesList.length === 0) {
    missingEvidences++;
  }
  evidenceCountsPerCase.push(evidencesList.length);

  // Check if initial evidence is in evidences list
  const initialMatches = evidencesList.some(tok => tok === rawInitialEvid || tok.startsWith(rawInitialEvid + '_@_'));
  if (!initialMatches) {
    initialEvidNotInEvidences++;
  }

  // Check token resolution
  for (let i = 0; i < evidencesList.length; i++) {
    totalTokenEvaluations++;
    const tok = evidencesList[i];
    let evidId = tok;
    let valKey = null;
    if (tok.includes('_@_')) {
      const p = tok.split('_@_');
      evidId = p[0];
      valKey = p[1];
    }
    if (!validEvidKeys.has(evidId)) {
      unresolvedTokens.add(tok);
    }
  }

  // 6. Differential Diagnosis parsing
  let diffs = [];
  try {
    diffs = JSON.parse(rawDiff.replace(/'/g, '"'));
  } catch (e) {
    missingDifferential++;
  }

  diffDiagnosisCounts.push(diffs.length);

  // Analyze differential ranking
  let foundInDiff = false;
  for (let r = 0; r < diffs.length; r++) {
    const [dName, prob] = diffs[r];
    if (dName === rawPathology) {
      foundInDiff = true;
      pathologyInDiffCount++;
      if (r === 0) pathologyTop1Count++;
      if (r < 3) pathologyTop3Count++;
      pathologyProbSum += prob;
      break;
    }
  }

  // 7. Duplicate detection (Normalized case fingerprint)
  // Sort evidences to normalize representation
  const sortedEvidsStr = evidencesList.slice().sort().join('|');
  const caseKey = `${age}_${rawSex}_${rawPathology}_${sortedEvidsStr}`;
  const seenCount = caseHashMap.get(caseKey) || 0;
  if (seenCount > 0) {
    exactDuplicateRows++;
  }
  caseHashMap.set(caseKey, seenCount + 1);

  if (totalRecords % 50000 === 0) {
    console.log(`Processed ${totalRecords} records...`);
  }
});

rl.on('close', () => {
  const elapsedSec = ((Date.now() - startTime) / 1000).toFixed(2);
  console.log(`\nCompleted audit of validation split in ${elapsedSec}s.`);
  console.log(`Total records: ${totalRecords}`);

  // Summary statistics
  ages.sort((a, b) => a - b);
  const medianAge = ages[Math.floor(ages.length / 2)];
  const meanAge = (ages.reduce((s, a) => s + a, 0) / ages.length).toFixed(1);
  const minAge = ages[0];
  const maxAge = ages[ages.length - 1];

  let pediatrics = 0; // 0-17
  let adults = 0;     // 18-64
  let geriatrics = 0; // 65+
  ages.forEach(a => {
    if (a < 18) pediatrics++;
    else if (a < 65) adults++;
    else geriatrics++;
  });

  evidenceCountsPerCase.sort((a, b) => a - b);
  const medianEvid = evidenceCountsPerCase[Math.floor(evidenceCountsPerCase.length / 2)];
  const meanEvid = (evidenceCountsPerCase.reduce((s, a) => s + a, 0) / evidenceCountsPerCase.length).toFixed(1);
  const minEvid = evidenceCountsPerCase[0];
  const maxEvid = evidenceCountsPerCase[evidenceCountsPerCase.length - 1];

  diffDiagnosisCounts.sort((a, b) => a - b);
  const medianDiff = diffDiagnosisCounts[Math.floor(diffDiagnosisCounts.length / 2)];
  const meanDiff = (diffDiagnosisCounts.reduce((s, a) => s + a, 0) / diffDiagnosisCounts.length).toFixed(1);

  console.log('\n--- Demographics ---');
  console.log(`Age: Min=${minAge}, Max=${maxAge}, Mean=${meanAge}, Median=${medianAge}`);
  console.log(`Age Groups: Pediatric(0-17)=${pediatrics} (${(pediatrics/totalRecords*100).toFixed(1)}%), Adult(18-64)=${adults} (${(adults/totalRecords*100).toFixed(1)}%), Geriatric(65+)=${geriatrics} (${(geriatrics/totalRecords*100).toFixed(1)}%)`);
  console.log(`Sex: Female=${sexCounts.F} (${(sexCounts.F/totalRecords*100).toFixed(1)}%), Male=${sexCounts.M} (${(sexCounts.M/totalRecords*100).toFixed(1)}%)`);

  console.log('\n--- Clinical Features per Case ---');
  console.log(`Evidences per Case: Min=${minEvid}, Max=${maxEvid}, Mean=${meanEvid}, Median=${medianEvid}`);
  console.log(`Differentials per Case: Mean=${meanDiff}, Median=${medianDiff}`);

  console.log('\n--- Ground Truth & Differential Alignment ---');
  console.log(`Ground truth pathology present in differential: ${pathologyInDiffCount} / ${totalRecords} (${(pathologyInDiffCount/totalRecords*100).toFixed(2)}%)`);
  console.log(`Ground truth is Top-1 candidate: ${pathologyTop1Count} (${(pathologyTop1Count/totalRecords*100).toFixed(2)}%)`);
  console.log(`Ground truth is Top-3 candidate: ${pathologyTop3Count} (${(pathologyTop3Count/totalRecords*100).toFixed(2)}%)`);
  console.log(`Mean ground truth probability: ${(pathologyProbSum/pathologyInDiffCount*100).toFixed(2)}%`);

  console.log('\n--- Integrity & Data Quality ---');
  console.log(`Missing fields: Age=${missingAge}, Sex=${missingSex}, Pathology=${missingPathology}, Evidences=${missingEvidences}, InitialEvid=${missingInitialEvid}`);
  console.log(`Invalid fields: Age=${invalidAge}, Sex=${invalidSex}, UnknownPathology=${unknownPathology}`);
  console.log(`Initial evidence NOT in evidences list: ${initialEvidNotInEvidences}`);
  console.log(`Total token evaluations: ${totalTokenEvaluations}`);
  console.log(`Unresolved evidence tokens: ${unresolvedTokens.size}`);
  if (unresolvedTokens.size > 0) {
    console.log('Unresolved samples:', Array.from(unresolvedTokens).slice(0, 10));
  }

  console.log('\n--- Duplicate Cases (within Validation) ---');
  console.log(`Unique case fingerprints: ${caseHashMap.size}`);
  console.log(`Exact duplicate cases inside validation split: ${exactDuplicateRows} (${(exactDuplicateRows/totalRecords*100).toFixed(2)}%)`);

  // Pathologies distribution
  const condKeys = Object.keys(conditionCounts);
  console.log(`\nUnique conditions represented in Validation: ${condKeys.length} / 49`);
  const sortedConds = Object.entries(conditionCounts).sort((a, b) => b[1] - a[1]);
  console.log('\nTop 5 Most Common Conditions:');
  sortedConds.slice(0, 5).forEach(([c, cnt]) => console.log(`  ${c}: ${cnt} (${(cnt/totalRecords*100).toFixed(2)}%)`));
  console.log('\nTop 5 Least Common Conditions:');
  sortedConds.slice(-5).forEach(([c, cnt]) => console.log(`  ${c}: ${cnt} (${(cnt/totalRecords*100).toFixed(2)}%)`));

  // Save validation summary to JSON for reporting
  const valSummary = {
    totalRecords,
    sha256,
    demographics: {
      minAge, maxAge, meanAge, medianAge,
      pediatrics, adults, geriatrics,
      females: sexCounts.F, males: sexCounts.M
    },
    evidences: {
      minEvid, maxEvid, meanEvid, medianEvid,
      meanDiff, medianDiff
    },
    differentialAccuracy: {
      presentPct: (pathologyInDiffCount/totalRecords*100).toFixed(2),
      top1Pct: (pathologyTop1Count/totalRecords*100).toFixed(2),
      top3Pct: (pathologyTop3Count/totalRecords*100).toFixed(2),
      meanProbPct: (pathologyProbSum/pathologyInDiffCount*100).toFixed(2)
    },
    dataQuality: {
      missingFields: missingAge + missingSex + missingPathology + missingEvidences + missingInitialEvid,
      invalidFields: invalidAge + invalidSex + unknownPathology,
      initialEvidNotInEvidences,
      unresolvedTokensCount: unresolvedTokens.size,
      exactDuplicateRows,
      exactDuplicatePct: (exactDuplicateRows/totalRecords*100).toFixed(2)
    },
    conditionDistribution: sortedConds
  };

  const outputDir = path.join(__dirname, '..', 'audit_output');
  fs.writeFileSync(path.join(outputDir, 'val_split_summary.json'), JSON.stringify(valSummary, null, 2), 'utf8');
  console.log('\nWrote val_split_summary.json');
});
