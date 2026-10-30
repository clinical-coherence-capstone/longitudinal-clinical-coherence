const fs = require('fs');
const readline = require('readline');
const path = require('path');

function parseCsvLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++; // skip escaped quote
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

const csvPath = path.join(__dirname, '..', 'working_data', 'release_validate_patients.csv');
const rl = readline.createInterface({
  input: fs.createReadStream(csvPath),
  crlfDelay: Infinity
});

let lineCount = 0;
rl.on('line', (line) => {
  if (lineCount < 5) {
    const fields = parseCsvLine(line);
    console.log(`Line ${lineCount} (${fields.length} fields):`);
    console.log('  AGE:', fields[0]);
    console.log('  DIFF len:', fields[1]?.length);
    console.log('  SEX:', fields[2]);
    console.log('  PATHOLOGY:', fields[3]);
    console.log('  EVIDENCES len:', fields[4]?.length);
    console.log('  INITIAL_EVIDENCE:', fields[5]);
  }
  lineCount++;
  if (lineCount === 5) {
    rl.close();
  }
});
