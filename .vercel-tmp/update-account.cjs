const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';
const baseUrl = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1';

function patch(table, filter, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const url = `${baseUrl}/${table}?${filter}`;
    const options = {
      method: 'PATCH',
      headers: {
        'apikey': serviceKey,
        'Authorization': 'Bearer ' + serviceKey,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
      }
    };
    const req = https.request(url, options, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve({ status: res.statusCode, data: d }));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function post(table, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const url = `${baseUrl}/${table}`;
    const options = {
      method: 'POST',
      headers: {
        'apikey': serviceKey,
        'Authorization': 'Bearer ' + serviceKey,
        'Content-Type': 'application/json',
        'Prefer': 'return=representation,resolve=deduplicate'
      }
    };
    const req = https.request(url, options, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve({ status: res.statusCode, data: d }));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function main() {
  console.log('Updating profiles table...');
  const profiles = await patch('profiles', 'mt5_account_id=eq.474194522', {
    mt5_account_id: '474202217',
    mt5_server: 'Exness-MT5Trial15',
    mt5_password: 'Kikokok3@'
  });
  console.log('Profiles:', profiles.status, profiles.data);

  console.log('\nUpdating bot_status table...');
  const botStatus = await patch('bot_status', 'mt5_account_id=eq.474194522', {
    mt5_account_id: '474202217'
  });
  console.log('Bot status:', botStatus.status, botStatus.data);

  console.log('\nUpdating grid_config table...');
  const gridConfig = await patch('grid_config', 'mt5_account_id=eq.474194522', {
    mt5_account_id: '474202217'
  });
  console.log('Grid config:', gridConfig.status, gridConfig.data);

  console.log('\nDone! Restart the bridge with: python mt5_bridge.py');
}

main().catch(console.error);
