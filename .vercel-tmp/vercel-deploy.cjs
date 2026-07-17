const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const isWindows = os.platform() === 'win32';

function log(msg) { console.error(msg); }

function commandExists(cmd) {
  try {
    if (isWindows) { return spawnSync('where', [cmd], { stdio: 'ignore' }).status === 0; }
    return spawnSync('sh', ['-c', 'command -v "$1"', '--', cmd], { stdio: 'ignore' }).status === 0;
  } catch { return false; }
}

function getCommandOutput(cmd, args) {
  try {
    const r = spawnSync(cmd, args, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'], shell: isWindows });
    return r.status === 0 ? (r.stdout || '').trim() : null;
  } catch { return null; }
}

function detectPkgMgr(p) {
  if (fs.existsSync(path.join(p, 'pnpm-lock.yaml'))) return 'pnpm';
  if (fs.existsSync(path.join(p, 'yarn.lock'))) return 'yarn';
  return 'npm';
}

log('========================================');
log('Vercel Production Deployment');
log('========================================');

if (!commandExists('vercel')) { log('Error: Vercel CLI not installed'); process.exit(1); }
log('Vercel CLI: ' + (getCommandOutput('vercel', ['--version']) || 'unknown'));

log('Checking login...');
try {
  const r = spawnSync('vercel', ['whoami'], { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], shell: isWindows });
  const out = (r.stdout || '').trim();
  if (r.status === 0 && out && !out.includes('Error')) { log('Logged in as: ' + out); }
  else { log('Not logged in'); process.exit(1); }
} catch { log('Not logged in'); process.exit(1); }

const proj = path.resolve('.');
const pkg = detectPkgMgr(proj);
log('\nBuilding with ' + pkg + '...');
const build = spawnSync(pkg, ['run', 'build'], { cwd: proj, stdio: 'inherit', shell: isWindows });
if (build.status !== 0) { log('Build FAILED'); process.exit(1); }
log('Build OK');

log('\nDeploying to production...');
const dep = spawnSync('vercel', ['--yes', '--prod'], {
  cwd: proj, encoding: 'utf8', stdio: ['inherit', 'pipe', 'pipe'], timeout: 300000, shell: isWindows
});
const output = (dep.stdout || '') + (dep.stderr || '');
log(output);
if (dep.status !== 0) { log('Deploy failed'); process.exit(1); }

const url = (output.match(/Aliased:\s*(https:\/\/[a-zA-Z0-9.-]+\.vercel\.app)/i) ||
             output.match(/Production:\s*(https:\/\/[a-zA-Z0-9.-]+\.vercel\.app)/i) || [])[1];
log('\n========================================');
log('Deployment successful!');
if (url) log('Live at: ' + url);
console.log(JSON.stringify({ status: 'success', url: url }));
