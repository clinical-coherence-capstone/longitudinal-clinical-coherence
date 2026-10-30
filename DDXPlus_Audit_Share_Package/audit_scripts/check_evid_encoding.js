const fs = require('fs');
const path = require('path');

const evidData = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'DDX Plus', 'release_evidences.json'), 'utf8'));

let emptyEn = 0;
let emptyFr = 0;
let enEncodingIssues = [];
let frEncodingIssues = [];

for (const [k, v] of Object.entries(evidData)) {
  if (!v.question_en || v.question_en.trim() === '') emptyEn++;
  if (!v.question_fr || v.question_fr.trim() === '') emptyFr++;

  if (v.question_en && (v.question_en.includes('\ufffd') || v.question_en.includes('Ã'))) {
    enEncodingIssues.push({ id: k, q: v.question_en });
  }
  if (v.question_fr && (v.question_fr.includes('\ufffd') || v.question_fr.includes('Ã'))) {
    frEncodingIssues.push({ id: k, q: v.question_fr });
  }
}

console.log('Empty English questions:', emptyEn);
console.log('Empty French questions:', emptyFr);
console.log('English question encoding issues:', enEncodingIssues.length);
console.log('French question encoding issues:', frEncodingIssues.length);

// Let's inspect value_meaning across all evidences
let totalValueCodes = 0;
const valueCodeMap = {};
for (const [k, v] of Object.entries(evidData)) {
  if (v.value_meaning) {
    for (const [vk, vm] of Object.entries(v.value_meaning)) {
      totalValueCodes++;
      if (!valueCodeMap[vk]) valueCodeMap[vk] = [];
      valueCodeMap[vk].push({ evidId: k, en: vm.en, fr: vm.fr });
    }
  }
}

console.log('Total value codes mapped:', totalValueCodes);
console.log('Unique value code keys:', Object.keys(valueCodeMap).length);
