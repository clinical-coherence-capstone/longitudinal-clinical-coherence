const fs = require('fs');
const path = require('path');

const filePath = path.join(__dirname, '..', 'DDX Plus', 'release_evidences.json');
const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));

const nonBinary = [];

for (const [k, v] of Object.entries(data)) {
  if (v.data_type !== 'B') {
    nonBinary.push({
      id: k,
      name: v.name,
      data_type: v.data_type,
      is_antecedent: v.is_antecedent,
      default_value: v.default_value,
      question_en: v.question_en,
      possible_values: v['possible-values'],
      value_meaning: v.value_meaning
    });
  }
}

console.log(`Found ${nonBinary.length} non-binary evidences (C & M):`);
nonBinary.forEach((item, idx) => {
  console.log(`\n--- [${idx + 1}] ID: ${item.id} | Type: ${item.data_type} | Antecedent: ${item.is_antecedent} ---`);
  console.log(`Question: ${item.question_en}`);
  console.log(`Default Value: ${item.default_value}`);
  console.log(`Possible Values (${item.possible_values ? item.possible_values.length : 0}):`, item.possible_values ? item.possible_values.slice(0, 10) : 'none');
  const meanings = Object.keys(item.value_meaning || {});
  console.log(`Value Meanings count: ${meanings.length}`);
  if (meanings.length > 0) {
    console.log(`Sample meanings:`, meanings.slice(0, 5).map(m => `${m} -> ${item.value_meaning[m].en}`));
  }
});
