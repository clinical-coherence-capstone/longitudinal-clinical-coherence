const fs = require('fs');
const path = require('path');

const inventory = [
  {
    path: 'Dataset Audit/DDX Plus.zip',
    type: 'Parent ZIP Archive',
    size_bytes: 178758020,
    records: 5,
    sha256: '4b051d9cbf5c9942ce0df86801ef73f13d633ea4395da93d950912711c21e6e2',
    parsed_ok: true,
    notes: 'Source distribution archive containing 5 release files'
  },
  {
    path: 'Dataset Audit/DDX Plus/release_conditions.json',
    type: 'JSON (Raw minified)',
    size_bytes: 20889,
    records: 49,
    sha256: '56edf4682d8e86a4209fc3a33932e50ce03d1cc1fecc326c26d5ef8fa5c24890',
    parsed_ok: true,
    notes: 'Dictionary of 49 pathology definitions, ICD-10 codes, severity tiers (1-5), and symptom/antecedent profiles'
  },
  {
    path: 'Dataset Audit/DDX Plus/release_evidences.json',
    type: 'JSON (Raw minified)',
    size_bytes: 120263,
    records: 223,
    sha256: '281c78b044ae60514e28ecc9052d08a8225dd3e2db3f00f8788b99c47b05e0c0',
    parsed_ok: true,
    notes: 'Dictionary of 223 clinical symptoms, physical findings, and medical antecedents with value sets'
  },
  {
    path: 'Dataset Audit/DDX Plus/release_validate_patients.zip',
    type: 'Nested ZIP Archive',
    size_bytes: 18706053,
    records: 1,
    sha256: '625a96855becf0efe5da339fd3d440aa99597d48f784957a97dacc3fceaa7e40',
    parsed_ok: true,
    notes: 'Contains uncompressed file release_validate_patients (87,371,169 bytes)'
  },
  {
    path: 'release_validate_patients.zip -> release_validate_patients',
    type: 'CSV (no extension)',
    size_bytes: 87371169,
    records: 132448,
    sha256: 'b84733533bff01daa1d47d27a0cd4d684bb54a0fc20d80aaee1250ff8ff989ed',
    parsed_ok: true,
    notes: 'Header: AGE,DIFFERENTIAL_DIAGNOSIS,SEX,PATHOLOGY,EVIDENCES,INITIAL_EVIDENCE. 0 missing fields, 0 unresolved tokens.'
  },
  {
    path: 'Dataset Audit/DDX Plus/release_test_patients.zip',
    type: 'Nested ZIP Archive',
    size_bytes: 18986243,
    records: 1,
    sha256: 'ad3bb981f3453fd7abffb35cc595a1c02197e409c581bff97c1265c33eb00d23',
    parsed_ok: true,
    notes: 'Contains uncompressed file release_test_patients (88,582,473 bytes)'
  },
  {
    path: 'release_test_patients.zip -> release_test_patients',
    type: 'CSV (no extension)',
    size_bytes: 88582473,
    records: 134529,
    sha256: 'f7ac3eae934c85780fc9b109a6cac5771540619a02690bee6fc0ab402baec186',
    parsed_ok: true,
    notes: 'Header: AGE,DIFFERENTIAL_DIAGNOSIS,SEX,PATHOLOGY,EVIDENCES,INITIAL_EVIDENCE. 0 missing fields, 0 unresolved tokens. 509 cross-split duplicates with validation.'
  },
  {
    path: 'Dataset Audit/DDX Plus/release_train_patients.zip',
    type: 'Nested ZIP Archive',
    size_bytes: 140923730,
    records: 1,
    sha256: '174ae1d56f36a15b7144838ecd214e1e1748a5369fc90c559529b6dc6ecfb218',
    parsed_ok: true,
    notes: 'Contains uncompressed file release_train_patients (670,584,506 bytes)'
  },
  {
    path: 'release_train_patients.zip -> release_train_patients',
    type: 'CSV (no extension)',
    size_bytes: 670584506,
    records: 1025602,
    sha256: '93933e9a9a7a00d618a931deda7767485af299fe4635bf189a7c63b510e8b172',
    parsed_ok: true,
    notes: 'Header: AGE,DIFFERENTIAL_DIAGNOSIS,SEX,PATHOLOGY,EVIDENCES,INITIAL_EVIDENCE. 0 missing fields, 0 unresolved tokens. 5,525 cross-split duplicates with val, 6,167 with test.'
  }
];

const escapeCsv = (str) => `"${String(str).replace(/"/g, '""')}"`;
const header = 'file_path,file_type,size_bytes,records,sha256_checksum,parsed_successfully,audit_notes';
const rows = inventory.map(item => [
  escapeCsv(item.path),
  escapeCsv(item.type),
  item.size_bytes,
  escapeCsv(item.records),
  escapeCsv(item.sha256),
  item.parsed_ok,
  escapeCsv(item.notes)
].join(','));

const outputDir = path.join(__dirname, '..', 'audit_output');
fs.writeFileSync(path.join(outputDir, '01_file_inventory.csv'), [header, ...rows].join('\n'), 'utf8');
console.log('01_file_inventory.csv generated successfully.');
