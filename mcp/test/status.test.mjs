import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { projectStatus } from '../dist/status.js';
test('live revisions include rules; router updates do not trigger costly board exports', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'circuit-live-'));
  const board = path.join(root, 'board.kicad_pcb');
  const project = {name:'test',root,board};
  try {
    await writeFile(board,'(kicad_pcb)');
    const first=await projectStatus(project);
    assert.deepEqual(await projectStatus(project),first);
    await writeFile(board+'.routing.json',JSON.stringify({backend:'fastroute',state:'running',message:'1s'}));
    const running=await projectStatus(project);
    assert.equal(running.revision,first.revision); assert.equal(running.routing.backend,'fastroute');
    await writeFile(board+'.routing.json','{');
    assert.equal((await projectStatus(project)).routing,null);
    await writeFile(board.replace('.kicad_pcb','.kicad_dru'),'(version 1)');
    assert.notEqual((await projectStatus(project)).revision,first.revision);
    const beforePolicy=await projectStatus(project);
    await writeFile(board.replace('.kicad_pcb','.routing-policy.json'),'{}');
    assert.notEqual((await projectStatus(project)).revision,beforePolicy.revision);
    await writeFile(board,'(kicad_pcb (segment))');
    assert.notEqual((await projectStatus(project)).revision,running.revision);
  } finally { await rm(root,{recursive:true,force:true}); }
});
