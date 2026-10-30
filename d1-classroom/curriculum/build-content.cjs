// Export projects from the canonical curriculum; never replace authored lesson text.
const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const lessons = JSON.parse(fs.readFileSync(path.join(__dirname, 'lessons.json'), 'utf8'));
assert.deepEqual(lessons.map(l => l.id), Array.from({ length: 16 }, (_, i) => i + 1));
const destination = path.join(__dirname, 'projects');fs.mkdirSync(destination, { recursive: true });
for (const lesson of lessons) {
  assert(lesson.blocks?.blocks?.blocks?.length > 0 && typeof lesson.code === 'string');
  assert.equal(lesson.steps.length, lesson.expected.length);
  const base = `第${String(lesson.id).padStart(2, '0')}課`;
  const project = { format: 'd1-classroom', version: 1, blocks: lesson.blocks, python: lesson.code,
    edited: !!lesson.codeOnly, mode: lesson.codeOnly ? 'python' : 'blocks', lesson: lesson.id };
  fs.writeFileSync(path.join(destination, base + '.d1.json'), JSON.stringify(project, null, 2) + '\n');
  fs.writeFileSync(path.join(destination, base + '.py'), lesson.code);
}
console.log('Exported 16 JSON and 16 Python projects from lessons.json');
