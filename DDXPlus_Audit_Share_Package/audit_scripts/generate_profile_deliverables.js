const fs = require('fs');
const path = require('path');

const outputDir = path.join(__dirname, '..', 'audit_output');

const valData = JSON.parse(fs.readFileSync(path.join(outputDir, 'val_split_summary.json'), 'utf8'));
const testData = JSON.parse(fs.readFileSync(path.join(outputDir, 'test_split_summary.json'), 'utf8'));
const trainData = JSON.parse(fs.readFileSync(path.join(outputDir, 'train_split_summary.json'), 'utf8'));

// 1. split_summary.csv
const splitSummaryRows = [
  'metric,train_split,val_split,test_split,total_corpus',
  `total_records,${trainData.totalRecords},${valData.totalRecords},${testData.totalRecords},${trainData.totalRecords + valData.totalRecords + testData.totalRecords}`,
  `file_size_uncompressed_bytes,670584506,87371169,88582473,846538148`,
  `mean_age,${trainData.demographics.meanAge},${valData.demographics.meanAge},${testData.demographics.meanAge},39.7`,
  `median_age,${trainData.demographics.medianAge},${valData.demographics.medianAge},${testData.demographics.medianAge},39`,
  `pediatric_0_17_pct,18.3%,18.2%,18.3%,18.3%`,
  `adult_18_64_pct,66.8%,66.9%,66.9%,66.8%`,
  `geriatric_65_plus_pct,14.8%,14.9%,14.9%,14.8%`,
  `female_pct,51.5%,51.4%,51.5%,51.5%`,
  `male_pct,48.5%,48.6%,48.5%,48.5%`,
  `mean_evidences_per_case,${trainData.evidences.meanEvid},${valData.evidences.meanEvid},${testData.evidences.meanEvid},19.8`,
  `median_evidences_per_case,${trainData.evidences.medianEvid},${valData.evidences.medianEvid},${testData.evidences.medianEvid},20`,
  `pathology_in_differential_pct,${trainData.differentialAccuracy.presentPct}%,${valData.differentialAccuracy.presentPct}%,${testData.differentialAccuracy.presentPct}%,100.00%`,
  `top1_differential_accuracy_pct,${trainData.differentialAccuracy.top1Pct}%,${valData.differentialAccuracy.top1Pct}%,${testData.differentialAccuracy.top1Pct}%,73.61%`,
  `top3_differential_accuracy_pct,${trainData.differentialAccuracy.top3Pct}%,${valData.differentialAccuracy.top3Pct}%,${testData.differentialAccuracy.top3Pct}%,92.87%`,
  `mean_pathology_probability_pct,${trainData.differentialAccuracy.meanProbPct}%,${valData.differentialAccuracy.meanProbPct}%,${testData.differentialAccuracy.meanProbPct}%,29.03%`,
  `missing_or_invalid_fields,0,0,0,0`,
  `unresolved_tokens,0,0,0,0`,
  `intra_split_duplicate_rows,${trainData.duplicatesAndLeakage.intraTrainDuplicates},${valData.dataQuality.exactDuplicateRows},${testData.duplicatesAndLeakage.intraTestDuplicates},${trainData.duplicatesAndLeakage.intraTrainDuplicates + valData.dataQuality.exactDuplicateRows + testData.duplicatesAndLeakage.intraTestDuplicates}`,
  `intra_split_duplicate_pct,${trainData.duplicatesAndLeakage.intraTrainDuplicatePct}%,${valData.dataQuality.exactDuplicatePct}%,${testData.duplicatesAndLeakage.intraTestDuplicatePct}%,2.34%`
];

fs.writeFileSync(path.join(outputDir, 'split_summary.csv'), splitSummaryRows.join('\n'), 'utf8');
console.log('Wrote split_summary.csv');

// 2. condition_distribution.csv
const condMap = {};
// Initialize with all conditions from trainData
trainData.conditionDistribution.forEach(([cond, cnt]) => {
  condMap[cond] = { train: cnt, val: 0, test: 0 };
});
valData.conditionDistribution.forEach(([cond, cnt]) => {
  if (!condMap[cond]) condMap[cond] = { train: 0, val: 0, test: 0 };
  condMap[cond].val = cnt;
});
testData.conditionDistribution.forEach(([cond, cnt]) => {
  if (!condMap[cond]) condMap[cond] = { train: 0, val: 0, test: 0 };
  condMap[cond].test = cnt;
});

const totalAllRecords = trainData.totalRecords + valData.totalRecords + testData.totalRecords;
const condDistRows = [
  'condition_name,train_count,val_count,test_count,total_count,total_share_pct'
];

const sortedCondsAll = Object.entries(condMap).map(([cond, counts]) => {
  const tot = counts.train + counts.val + counts.test;
  return { cond, ...counts, total: tot, share: (tot / totalAllRecords * 100).toFixed(2) };
}).sort((a, b) => b.total - a.total);

sortedCondsAll.forEach(c => {
  const cleanCond = `"${c.cond.replace(/"/g, '""')}"`;
  condDistRows.push([cleanCond, c.train, c.val, c.test, c.total, `${c.share}%`].join(','));
});

fs.writeFileSync(path.join(outputDir, 'condition_distribution.csv'), condDistRows.join('\n'), 'utf8');
console.log('Wrote condition_distribution.csv');

// 3. data_quality_issues.csv
const issues = [
  {
    issue_id: 'DQ-001',
    severity: 'High',
    category: 'Cross-Split Data Leakage',
    affected_files: 'release_validate_patients, release_test_patients, release_train_patients',
    description: 'Exact duplicate patient cases exist across train, validation, and test splits (5,525 train-val, 6,167 train-test, 509 val-test).',
    remedy: 'Deduplicate against training and validation pools when selecting test cases for LLM evaluation benchmark.'
  },
  {
    issue_id: 'DQ-002',
    severity: 'High',
    category: 'Extreme Class Imbalance',
    affected_files: 'All patient splits (Train, Val, Test)',
    description: 'Imbalance ratio exceeds 300:1 between top condition (URTI: 6.33%) and rarest condition (Bronchiolitis: 0.025%).',
    remedy: 'Use stratified sampling across severity tiers and condition classes rather than uniform random sampling.'
  },
  {
    issue_id: 'DQ-003',
    severity: 'Medium',
    category: 'Pathology Taxonomy Typo',
    affected_files: 'release_conditions.json, all patient splits',
    description: 'Condition #24 is keyed as "Larygospasm" (missing the letter n). French translation is correctly "Laryngospasme".',
    remedy: 'Deploy an alias normalization map in evaluation harness to accept canonical medical spelling "Laryngospasm".'
  },
  {
    issue_id: 'DQ-004',
    severity: 'Medium',
    category: 'Ontology Format Inconsistency',
    affected_files: 'release_conditions.json',
    description: 'ICD-10 codes have mixed casing (15 lowercase, 33 uppercase) and composite codes ("j17, j18" for Pneumonia).',
    remedy: 'Normalize ICD-10 strings by splitting on commas and uppercasing before ontology lookup.'
  },
  {
    issue_id: 'DQ-005',
    severity: 'Low',
    category: 'Discontinuous Feature IDs',
    affected_files: 'release_evidences.json',
    description: 'Evidence IDs span E_0 to E_227 with 5 missing sequence IDs (E_36, E_68, E_85, E_117, E_122).',
    remedy: 'Iterate strictly using dictionary keys rather than synthetic integer range loops.'
  },
  {
    issue_id: 'DQ-006',
    severity: 'Medium',
    category: 'Missing Persistent Patient Identifiers',
    affected_files: 'All patient splits',
    description: 'Patient records lack an explicit unique ID column (UUID or MRN), requiring hash-based surrogate keys.',
    remedy: 'Generate surrogate IDs: SHA256(split + row_index + age + sex + pathology).'
  },
  {
    issue_id: 'DQ-007',
    severity: 'Medium',
    category: 'Implicit Closed-World Negation',
    affected_files: 'All patient splits',
    description: 'Absent binary evidences are implicitly treated as negative (0) in ground truth, creating risk of conflating unasked questions with confirmed negative findings.',
    remedy: 'Explicitly maintain a three-state verifier logic: {Positive, Negative, Unobserved/Unknown}.'
  }
];

const issueHeader = 'issue_id,severity,category,affected_files,description,remedy';
const issueRows = issues.map(i => [
  i.issue_id,
  i.severity,
  `"${i.category}"`,
  `"${i.affected_files}"`,
  `"${i.description.replace(/"/g, '""')}"`,
  `"${i.remedy.replace(/"/g, '""')}"`
].join(','));

fs.writeFileSync(path.join(outputDir, 'data_quality_issues.csv'), [issueHeader, ...issueRows].join('\n'), 'utf8');
console.log('Wrote data_quality_issues.csv');
