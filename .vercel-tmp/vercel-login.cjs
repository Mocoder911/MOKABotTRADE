#!/usr/bin/env node
const { spawnSync, spawn } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const isWindows = os.platform() === 'win32';

const tmpDir = path.join(process.cwd(), '.vercel-tmp');
if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });
const LOG_FILE = path.join(tmpDir, 'login.log');

function log(msg) { console.error(msg); }

function commandExists(cmd) {
  try {
    if (isWindows) {
      return spawnSync('where', [cmd], { stdio: 'ignore' }).status === 0;
    } else {
      return spawnSync('sh', ['-c', `command -v "$1"`, '--', cmd], { stdio: 'ignore' }).status === 0;
    }
  } catch { return false; }
}

function getCommandOutput(cmd, args) {
  try {
    const result = spawnSync(cmd, args, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'ignore'], shell: isWindows });
    return result.status === 0 ? (result.stdout || '').trim() : null;
  } catch { return null; }
}

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

async function main() {
  log('========================================');
  log('Vercel CLI Login');
  log('========================================');
  log('');

  if (!commandExists('vercel')) {
    log('Error: Vercel CLI is not installed');
    process.exit(1);
  }

  const version = getCommandOutput('vercel', ['--version']) || 'unknown';
  log(`Vercel CLI version: ${version}`);

  // Check login status
  log('Checking login status...');
  try {
    const result = spawnSync('vercel', ['whoami'], { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], shell: isWindows });
    const output = (result.stdout || '').trim();
    if (result.status === 0 && output) {
      log(`Already logged in as: ${output}`);
      console.log(JSON.stringify({ status: 'already_logged_in', message: `Already logged in as ${output}` }));
      process.exit(0);
    }
  } catch {}

  log('');
  log('Starting login...');
  
  // Start background login process
  const logStream = fs.openSync(LOG_FILE, 'w');
  const child = spawn('vercel', ['login'], {
    detached: true,
    stdio: ['ignore', logStream, logStream],
    shell: isWindows
  });
  child.unref();
  log(`Background login process started (PID: ${child.pid})`);

  // Wait for URL
  log('Waiting for authorization URL...');
  let authUrl = null;
  for (let i = 0; i < 40; i++) {
    await sleep(500);
    try {
      if (fs.existsSync(LOG_FILE)) {
        const content = fs.readFileSync(LOG_FILE, 'utf8');
        const match = content.match(/https:\/\/vercel\.com\/oauth\/device\?user_code=[A-Z0-9-]+/);
        if (match) {
          authUrl = match[0];
          break;
        }
      }
    } catch {}
  }

  if (authUrl) {
    log('');
    log('========================================');
    log('Authorization URL extracted');
    log('========================================');
    log('');
    
    // Open browser
    try {
      if (isWindows) {
        spawnSync('powershell', ['-Command', `Start-Process '${authUrl}'`], { stdio: 'ignore', windowsHide: true });
      } else if (os.platform() === 'darwin') {
        spawnSync('open', [authUrl], { stdio: 'ignore' });
      } else {
        spawnSync('xdg-open', [authUrl], { stdio: 'ignore' });
      }
      log('Browser opened automatically');
    } catch {
      log('Failed to open browser, please open manually');
    }
    
    console.log(JSON.stringify({ status: 'needs_auth', auth_url: authUrl, log_file: LOG_FILE }));
  } else {
    log('Failed to get authorization URL');
    try {
      log('Log content: ' + fs.readFileSync(LOG_FILE, 'utf8'));
    } catch {}
    process.exit(1);
  }
}

main();
