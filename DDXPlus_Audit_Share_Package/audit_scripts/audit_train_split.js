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

const trainCsvPath = path.join(__dirname, '..', 'working_data', 'release_train_patients.csv');
const valCsvPath = path.join(__dirname, '..', 'working_data', 'release_validate_patients.csv');
const testCsvPath = path.join(__dirname, '..', 'working_data', 'release_test_patients.csv');

// Fast CSV parser
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

// Step 1: Compute SHA-256 of release_train_patients.csv via stream
console.log('Calculating SHA-256 of release_train_patients.csv...');
const hash = crypto.createHash('sha256');
const hashStream = fs.createReadStream(trainCsvPath);
hashStream.on('data', chunk => hash.update(chunk));
hashStream.on('end', () => {
  const trainSha256 = hash.digest('hex');
  console.log('Train CSV SHA-256:', trainSha256);
  loadValidationAndTestFingerprints(trainSha256);
});

// Step 2: Load Val and Test fingerprints
const valFingerprints = new Set();
const testFingerprints = new Set();

function loadValidationAndTestFingerprints(trainSha256) {
  console.log('Loading validation fingerprints...');
  const valRl = readline.createInterface({
    input: fs.createReadStream(valCsvPath),
    crlfDelay: Infinity
  });

  let valHeader = false;
  valRl.on('line', (line) => {
    if (!valHeader) { valHeader = true; return; }
    const f = parseCsvLine(line);
    if (f.length >= 6) {
      let evids = [];
      try { evids = JSON.parse(f[4].replace(/'/g, '"')); } catch(e) {
        evids = f[4].replace(/[\[\]']/g, '').split(',').map(s=>s.trim()).filter(Boolean);
      }
      valFingerprints.add(`${f[0]}_${f[2]}_${f[3]}_${evids.slice().sort().join('|')}`);
    }
  });

  valRl.on('close', () => {
    console.log(`Loaded ${valFingerprints.size} validation fingerprints.`);
    console.log('Loading test fingerprints...');
    const testRl = readline.createInterface({
      input: fs.createReadStream(testCsvPath),
      crlfDelay: Infinity
    });

    let testHeader = false;
    testRl.on('line', (line) => {
      if (!testHeader) { testHeader = true; return; }
      const f = parseCsvLine(line);
      if (f.length >= 6) {
        let evids = [];
        try { evids = JSON.parse(f[4].replace(/'/g, '"')); } catch(e) {
          evids = f[4].replace(/[\[\]']/g, '').split(',').map(s=>s.trim()).filter(Boolean);
        }
        testFingerprints.add(`${f[0]}_${f[2]}_${f[3]}_${evids.slice().sort().join('|')}`);
      }
    });

    testRl.on('close', () => {
      console.log(`Loaded ${testFingerprints.size} test fingerprints.`);
      auditTrainSplit(trainSha256);
    });
  });
}

// Step 3: Stream audit train split
function auditTrainSplit(trainSha256) {
  console.log('Streaming and auditing training split records (670 MB)...');
  const startTime = Date.now();
  const trainRl = readline.createInterface({
    input: fs.createReadStream(trainCsvPath),
    crlfDelay: Infinity
  });

  let totalRecords = 0;
  let headerSeen = false;

  const sexCounts = { M: 0, F: 0, other: 0 };
  let pediatrics = 0, adults = 0, geriatrics = 0;
  let ageSum = 0;
  let minAge = 999, maxAge = -1;
  const ageBuckets = new Int32Array(130);

  const conditionCounts = {};
  let evidSum = 0;
  let minEvid = 999, maxEvid = -1;
  const evidBuckets = new Int32Array(100);

  let missingAge = 0, invalidAge = 0;
  let missingSex = 0, invalidSex = 0;
  let missingPathology = 0, unknownPathology = 0;
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

  // Duplicates tracking
  const trainFingerprints = new Set();
  let exactDuplicatesInTrain = 0;
  let crossSplitLeakageWithVal = 0;
  let crossSplitLeakageWithTest = 0;

  trainRl.on('line', (line) => {
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
      else {
        ageSum += age;
        if (age < minAge) minAge = age;
        if (age > maxAge) maxAge = age;
        ageBuckets[age]++;
        if (age < 18) pediatrics++;
        else if (age < 65) adults++;
        else geriatrics++;
      }
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
    }

    // Evidences
    let evidencesList = [];
    try {
      evidencesList = JSON.parse(rawEvidences.replace(/'/g, '"'));
    } catch (e) {
      evidencesList = rawEvidences.replace(/[\[\]']/g, '').split(',').map(s => s.trim()).filter(Boolean);
    }

    const nEvids = evidencesList.length;
    if (nEvids === 0) missingEvidences++;
    evidSum += nEvids;
    if (nEvids < minEvid) minEvid = nEvids;
    if (nEvids > maxEvid) maxEvid = nEvids;
    if (nEvids < 100) evidBuckets[nEvids]++;

    // Initial evidence check
    const initialMatches = evidencesList.some(tok => tok === rawInitialEvid || tok.startsWith(rawInitialEvid + '_@_'));
    if (!initialMatches) initialEvidNotInEvidences++;

    // Token resolution
    for (let i = 0; i < nEvids; i++) {
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

    // Intra-train duplicates
    if (trainFingerprints.has(fp)) {
      exactDuplicatesInTrain++;
    } else {
      trainFingerprints.add(fp);
    }

    // Cross-split leakage
    if (valFingerprints.has(fp)) crossSplitLeakageWithVal++;
    if (testFingerprints.has(fp)) crossSplitLeakageWithTest++;

    if (totalRecords % 250000 === 0) {
      console.log(`Processed ${totalRecords} train records...`);
    }
  });

  trainRl.on('close', () => {
    const elapsedSec = ((Date.now() - startTime) / 1000).toFixed(2);
    console.log(`\nCompleted audit of training split in ${elapsedSec}s.`);
    console.log(`Total training records: ${totalRecords}`);

    // Median age from buckets
    let half = totalRecords / 2;
    let running = 0, medianAge = 0;
    for (let i = 0; i < ageBuckets.length; i++) {
      running += ageBuckets[i];
      if (running >= half) { medianAge = i; break; }
    }
    const meanAge = (ageSum / totalRecords).toFixed(1);

    // Median evidences from buckets
    running = 0;
    let medianEvid = 0;
    for (let i = 0; i < evidBuckets.length; i++) {
      running += evidBuckets[i];
      if (running >= half) { medianEvid = i; break; }
    }
    const meanEvid = (evidSum / totalRecords).toFixed(1);

    console.log('\n--- Train Demographics ---');
    console.log(`Age: Min=${minAge}, Max=${maxAge}, Mean=${meanAge}, Median=${medianAge}`);
    console.log(`Age Groups: Pediatric(0-17)=${pediatrics} (${(pediatrics/totalRecords*100).toFixed(1)}%), Adult(18-64)=${adults} (${(adults/totalRecords*100).toFixed(1)}%), Geriatric(65+)=${geriatrics} (${(geriatrics/totalRecords*100).toFixed(1)}%)`);
    console.log(`Sex: Female=${sexCounts.F} (${(sexCounts.F/totalRecords*100).toFixed(1)}%), Male=${sexCounts.M} (${(sexCounts.M/totalRecords*100).toFixed(1)}%)`);

    console.log('\n--- Clinical Features per Case ---');
    console.log(`Evidences per Case: Min=${minEvid}, Max=${maxEvid}, Mean=${meanEvid}, Median=${medianEvid}`);

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
    console.log(`Unique case fingerprints in Train: ${trainFingerprints.size}`);
    console.log(`Exact duplicate cases inside Train split: ${exactDuplicatesInTrain} (${(exactDuplicatesInTrain/totalRecords*100).toFixed(2)}%)`);
    console.log(`CROSS-SPLIT LEAKAGE (Train cases identical to a Validation case): ${crossSplitLeakageWithVal} (${(crossSplitLeakageWithVal/totalRecords*100).toFixed(2)}%)`);
    console.log(`CROSS-SPLIT LEAKAGE (Train cases identical to a Test case): ${crossSplitLeakageWithTest} (${(crossSplitLeakageWithTest/totalRecords*100).toFixed(2)}%)`);

    const sortedConds = Object.entries(conditionCounts).sort((a, b) => b[1] - a[1]);
    console.log(`\nUnique conditions represented in Train: ${sortedConds.length} / 49`);
    console.log('Top 3 conditions:', sortedConds.slice(0, 3));
    console.log('Bottom 3 conditions:', sortedConds.slice(-3));

    const trainSummary = {
      totalRecords,
      sha256: trainSha256,
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
        intraTrainDuplicates: exactDuplicatesInTrain,
        intraTrainDuplicatePct: (exactDuplicatesInTrain/totalRecords*100).toFixed(2),
        crossSplitLeakageTrainVal: crossSplitLeakageWithVal,
        crossSplitLeakageTrainValPct: (crossSplitLeakageWithVal/totalRecords*100).toFixed(2),
        crossSplitLeakageTrainTest: crossSplitLeakageWithTest,
        crossSplitLeakageTrainTestPct: (crossSplitLeakageWithTest/totalRecords*100).toFixed(2)
      },
      conditionDistribution: sortedConds
    };

    const outputDir = path.join(__dirname, '..', 'audit_output');
    fs.writeFileSync(path.join(outputDir, 'train_split_summary.json'), JSON.stringify(trainSummary, null, 2), 'utf8');
    console.log('\nWrote train_split_summary.json');
  });
}
