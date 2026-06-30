#!/usr/bin/env node
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const isWindows = os.platform() === 'win32';

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

function detectPackageManager(projectPath) {
  if (fs.existsSync(path.join(projectPath, 'pnpm-lock.yaml'))) return 'pnpm';
  if (fs.existsSync(path.join(projectPath, 'yarn.lock'))) return 'yarn';
  if (fs.existsSync(path.join(projectPath, 'package-lock.json'))) return 'npm';
  return 'npm';
}

function main() {
  log('========================================');
  log('Vercel CLI Deployment');
  log('========================================');
  log('');

  if (!commandExists('vercel')) {
    log('Error: Vercel CLI is not installed');
    process.exit(1);
  }

  const version = getCommandOutput('vercel', ['--version']) || 'unknown';
  log(`Vercel CLI version: ${version}`);

  // Check login
  log('Checking login status...');
  try {
    const result = spawnSync('vercel', ['whoami'], { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'], shell: isWindows });
    const output = (result.stdout || '').trim();
    if (result.status === 0 && output) {
      log(`Logged in as: ${output}`);
    } else {
      log('Error: Not logged in');
      process.exit(1);
    }
  } catch {
    log('Error: Not logged in');
    process.exit(1);
  }

  const projectPath = '.';
  const pkgManager = detectPackageManager(projectPath);
  log(`Package manager: ${pkgManager}`);

  // Run build
  log('');
  log('Running build...');
  const buildResult = spawnSync(pkgManager, ['run', 'build'], {
    cwd: projectPath,
    stdio: 'inherit',
    shell: isWindows
  });
  if (buildResult.status !== 0) {
    log('Build failed!');
    process.exit(1);
  }
  log('Build completed!');

  // Deploy
  log('');
  log('Deploying to production...');
  const deployResult = spawnSync('vercel', ['--yes', '--prod'], {
    cwd: projectPath,
    encoding: 'utf8',
    stdio: ['inherit', 'pipe', 'pipe'],
    timeout: 300000,
    shell: isWindows
  });

  const output = (deployResult.stdout || '') + (deployResult.stderr || '');
  log(output);

  if (deployResult.status !== 0) {
    log('Deployment failed!');
    process.exit(1);
  }

  // Extract URL
  const aliasedMatch = output.match(/Aliased:\s*(https:\/\/[a-zA-Z0-9.-]+\.vercel\.app)/i);
  const productionMatch = output.match(/Production:\s*(https:\/\/[a-zA-Z0-9.-]+\.vercel\.app)/i);
  const finalUrl = aliasedMatch?.[1] || productionMatch?.[1];

  log('');
  log('========================================');
  log('Deployment successful!');
  log('========================================');
  if (finalUrl) {
    log(`Your site is live: ${finalUrl}`);
  }
  console.log(JSON.stringify({ status: 'success', url: finalUrl }));
}

main();
