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

const testCsvPath = path.join(__dirname, '..', 'working_data', 'release_test_patients.csv');
const valCsvPath = path.join(__dirname, '..', 'working_data', 'release_validate_patients.csv');

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

// Step 1: Compute SHA-256 of release_test_patients.csv
console.log('Calculating SHA-256 of release_test_patients.csv...');
const testBuf = fs.readFileSync(testCsvPath);
const testSha256 = crypto.createHash('sha256').update(testBuf).digest('hex');
console.log('Test CSV SHA-256:', testSha256);
console.log('Test CSV size (bytes):', testBuf.length);

// Step 2: Build validation fingerprint set for cross-split leakage
console.log('Loading validation fingerprints to check cross-split leakage...');
const valFingerprints = new Set();
const valRl = readline.createInterface({
  input: fs.createReadStream(valCsvPath),
  crlfDelay: Infinity
});

let valHeaderSeen = false;
valRl.on('line', (line) => {
  if (!valHeaderSeen) { valHeaderSeen = true; return; }
  const fields = parseCsvLine(line);
  if (fields.length >= 6) {
    const age = fields[0];
    const sex = fields[2];
    const pathol = fields[3];
    const rawEvids = fields[4];
    let evids = [];
    try {
      evids = JSON.parse(rawEvids.replace(/'/g, '"'));
    } catch (e) {
      evids = rawEvids.replace(/[\[\]']/g, '').split(',').map(s => s.trim()).filter(Boolean);
    }
    const fp = `${age}_${sex}_${pathol}_${evids.slice().sort().join('|')}`;
    valFingerprints.add(fp);
  }
});

valRl.on('close', () => {
  console.log(`Loaded ${valFingerprints.size} unique validation case fingerprints.`);
  auditTestSplit();
});

function auditTestSplit() {
  console.log('Auditing test split records...');
  const testRl = readline.createInterface({
    input: fs.createReadStream(testCsvPath),
    crlfDelay: Infinity
  });

  let totalRecords = 0;
  let headerSeen = false;

  const sexCounts = { M: 0, F: 0, other: 0 };
  const ages = [];
  const conditionCounts = {};
  const initialEvidCounts = {};
  const evidenceCountsPerCase = [];
  const diffDiagnosisCounts = [];

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

  const unresolvedTokens = new Set();
  let totalTokenEvaluations = 0;

  let pathologyInDiffCount = 0;
  let pathologyTop1Count = 0;
  let pathologyTop3Count = 0;
  let pathologyProbSum = 0;

  const testHashMap = new Map();
  let exactDuplicatesInTest = 0;
  let crossSplitDuplicatesWithVal = 0;

  const startTime = Date.now();

  testRl.on('line', (line) => {
    if (!headerSeen) {
      headerSeen = true;
      return;
    }

    totalRecords++;
    const fields = parseCsvLine(line);
    if (fields.length < 6) return;

    const rawAge = fields[0];
    const rawDiff = fields[1];
    const rawSex = fields[2];
    const rawPathology = fields[3];
    const rawEvidences = fields[4];
    const rawInitialEvid = fields[5];

    // Age
    const age = parseInt(rawAge, 10);
    if (isNaN(age)) {
      missingAge++;
    } else {
      if (age < 0 || age > 130) invalidAge++;
      ages.push(age);
    }

    // Sex
    if (rawSex === 'M' || rawSex === 'F') {
      sexCounts[rawSex]++;
    } else {
      if (!rawSex) missingSex++;
      else invalidSex++;
      sexCounts.other++;
    }

    // Pathology
    if (!rawPathology) {
      missingPathology++;
    } else {
      if (!validCondKeys.has(rawPathology)) unknownPathology++;
      conditionCounts[rawPathology] = (conditionCounts[rawPathology] || 0) + 1;
    }

    // Initial Evidence
    if (!rawInitialEvid) {
      missingInitialEvid++;
    } else {
      initialEvidCounts[rawInitialEvid] = (initialEvidCounts[rawInitialEvid] || 0) + 1;
    }

    // Evidences
    let evidencesList = [];
    try {
      evidencesList = JSON.parse(rawEvidences.replace(/'/g, '"'));
    } catch (e) {
      evidencesList = rawEvidences.replace(/[\[\]']/g, '').split(',').map(s => s.trim()).filter(Boolean);
    }

    if (evidencesList.length === 0) missingEvidences++;
    evidenceCountsPerCase.push(evidencesList.length);

    // Initial evidence in evidences list
    const initialMatches = evidencesList.some(tok => tok === rawInitialEvid || tok.startsWith(rawInitialEvid + '_@_'));
    if (!initialMatches) initialEvidNotInEvidences++;

    // Tokens resolution
    for (let i = 0; i < evidencesList.length; i++) {
      totalTokenEvaluations++;
      const tok = evidencesList[i];
      let evidId = tok;
      if (tok.includes('_@_')) evidId = tok.split('_@_')[0];
      if (!validEvidKeys.has(evidId)) unresolvedTokens.add(tok);
    }

    // Differential
    let diffs = [];
    try {
      diffs = JSON.parse(rawDiff.replace(/'/g, '"'));
    } catch (e) {
      missingDifferential++;
    }
    diffDiagnosisCounts.push(diffs.length);

    for (let r = 0; r < diffs.length; r++) {
      const [dName, prob] = diffs[r];
      if (dName === rawPathology) {
        pathologyInDiffCount++;
        if (r === 0) pathologyTop1Count++;
        if (r < 3) pathologyTop3Count++;
        pathologyProbSum += prob;
        break;
      }
    }

    // Fingerprint
    const sortedEvidsStr = evidencesList.slice().sort().join('|');
    const fp = `${age}_${rawSex}_${rawPathology}_${sortedEvidsStr}`;

    // Intra-test duplicates
    const seen = testHashMap.get(fp) || 0;
    if (seen > 0) exactDuplicatesInTest++;
    testHashMap.set(fp, seen + 1);

    // Cross-split leakage with validation
    if (valFingerprints.has(fp)) {
      crossSplitDuplicatesWithVal++;
    }

    if (totalRecords % 50000 === 0) {
      console.log(`Processed ${totalRecords} test records...`);
    }
  });

  testRl.on('close', () => {
    const elapsedSec = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`\nCompleted audit of test split in ${elapsedSec}s.`);
    console.log(`Total test records: ${totalRecords}`);

    ages.sort((a, b) => a - b);
    const medianAge = ages[Math.floor(ages.length / 2)];
    const meanAge = (ages.reduce((s, a) => s + a, 0) / ages.length).toFixed(1);
    const minAge = ages[0];
    const maxAge = ages[ages.length - 1];

    let pediatrics = 0, adults = 0, geriatrics = 0;
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

    console.log('\n--- Test Demographics ---');
    console.log(`Age: Min=${minAge}, Max=${maxAge}, Mean=${meanAge}, Median=${medianAge}`);
    console.log(`Age Groups: Pediatric(0-17)=${pediatrics} (${(pediatrics/totalRecords*100).toFixed(1)}%), Adult(18-64)=${adults} (${(adults/totalRecords*100).toFixed(1)}%), Geriatric(65+)=${geriatrics} (${(geriatrics/totalRecords*100).toFixed(1)}%)`);
    console.log(`Sex: Female=${sexCounts.F} (${(sexCounts.F/totalRecords*100).toFixed(1)}%), Male=${sexCounts.M} (${(sexCounts.M/totalRecords*100).toFixed(1)}%)`);

    console.log('\n--- Clinical Features per Case ---');
    console.log(`Evidences per Case: Min=${minEvid}, Max=${maxEvid}, Mean=${meanEvid}, Median=${medianEvid}`);
    console.log(`Differentials evaluated: ${diffDiagnosisCounts.length}`);

    console.log('\n--- Ground Truth & Differential Alignment ---');
    console.log(`Ground truth in differential: ${pathologyInDiffCount} / ${totalRecords} (${(pathologyInDiffCount/totalRecords*100).toFixed(2)}%)`);
    console.log(`Ground truth is Top-1: ${pathologyTop1Count} (${(pathologyTop1Count/totalRecords*100).toFixed(2)}%)`);
    console.log(`Ground truth is Top-3: ${pathologyTop3Count} (${(pathologyTop3Count/totalRecords*100).toFixed(2)}%)`);
    console.log(`Mean ground truth prob: ${(pathologyProbSum/pathologyInDiffCount*100).toFixed(2)}%`);

    console.log('\n--- Integrity & Data Quality ---');
    console.log(`Missing fields: Age=${missingAge}, Sex=${missingSex}, Pathology=${missingPathology}, Evidences=${missingEvidences}, InitialEvid=${missingInitialEvid}`);
    console.log(`Invalid fields: Age=${invalidAge}, Sex=${invalidSex}, UnknownPathology=${unknownPathology}`);
    console.log(`Initial evidence NOT in evidences list: ${initialEvidNotInEvidences}`);
    console.log(`Total token evaluations: ${totalTokenEvaluations}`);
    console.log(`Unresolved evidence tokens: ${unresolvedTokens.size}`);

    console.log('\n--- Duplicates & Cross-Split Leakage ---');
    console.log(`Unique case fingerprints in Test: ${testHashMap.size}`);
    console.log(`Exact duplicate cases inside Test split: ${exactDuplicatesInTest} (${(exactDuplicatesInTest/totalRecords*100).toFixed(2)}%)`);
    console.log(`CROSS-SPLIT LEAKAGE (Test cases identical to a Validation case): ${crossSplitDuplicatesWithVal} (${(crossSplitDuplicatesWithVal/totalRecords*100).toFixed(2)}%)`);

    const sortedConds = Object.entries(conditionCounts).sort((a, b) => b[1] - a[1]);
    console.log(`\nUnique conditions represented in Test: ${sortedConds.length} / 49`);
    console.log('Top 3 conditions:', sortedConds.slice(0, 3));
    console.log('Bottom 3 conditions:', sortedConds.slice(-3));

    const testSummary = {
      totalRecords,
      sha256: testSha256,
      demographics: {
        minAge, maxAge, meanAge, medianAge,
        pediatrics, adults, geriatrics,
        females: sexCounts.F, males: sexCounts.M
      },
      evidences: {
        minEvid, maxEvid, meanEvid, medianEvid
      },
      differentialAccuracy: {
        presentPct: (pathologyInDiffCount/totalRecords*100).toFixed(2),
        top1Pct: (pathologyTop1Count/totalRecords*100).toFixed(2),
        top3Pct: (pathologyTop3Count/totalRecords*100).toFixed(2),
        meanProbPct: (pathologyProbSum/pathologyInDiffCount*100).toFixed(2)
      },
      duplicatesAndLeakage: {
        intraTestDuplicates: exactDuplicatesInTest,
        intraTestDuplicatePct: (exactDuplicatesInTest/totalRecords*100).toFixed(2),
        crossSplitLeakageValTest: crossSplitDuplicatesWithVal,
        crossSplitLeakageValTestPct: (crossSplitDuplicatesWithVal/totalRecords*100).toFixed(2)
      },
      conditionDistribution: sortedConds
    };

    const outputDir = path.join(__dirname, '..', 'audit_output');
    fs.writeFileSync(path.join(outputDir, 'test_split_summary.json'), JSON.stringify(testSummary, null, 2), 'utf8');
    console.log('\nWrote test_split_summary.json');
  });
}
