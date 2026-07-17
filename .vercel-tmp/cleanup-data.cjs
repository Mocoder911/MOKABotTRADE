const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';
const baseUrl = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1';

function request(method, url, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const options = {
      method: method,
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
    if (data) req.write(data);
    req.end();
  });
}

async function main() {
  console.log('=== Clean Up Wrong Data ===\n');

  // User IDs
  const MO_USER_ID = '41e69c7f-f87a-4b40-9b87-bd675b384b9d';
  const KARIM_USER_ID = '58a3b12f-5dac-47f9-99f9-973cfd2f8ad9';
  const LOVELYFISH_USER_ID = '8b04ae08-7e7d-4d98-ae55-6aa17f113f83';

  // 1. Delete wrong balance entries
  console.log('1. Cleaning up wrong balance entries...');
  
  // Delete lovelyfish (old user)
  const del1 = await request('DELETE', `${baseUrl}/account_balance?user_id=eq.${LOVELYFISH_USER_ID}`);
  console.log(`   Deleted lovelyfish balance: ${del1.status}`);

  // Delete Karim's wrong balance (he shouldn't have $1097)
  const del2 = await request('DELETE', `${baseUrl}/account_balance?user_id=eq.${KARIM_USER_ID}`);
  console.log(`   Deleted Karim's wrong balance: ${del2.status}`);

  // Delete mo's wrong balance (it's from the wrong account)
  const del3 = await request('DELETE', `${baseUrl}/account_balance?user_id=eq.${MO_USER_ID}`);
  console.log(`   Deleted mo's wrong balance: ${del3.status}`);

  // 2. Clean up old bot_status entries
  console.log('\n2. Cleaning up old bot_status entries...');
  const oldAccounts = ['7400819', '260904217', '474194522'];
  for (const acc of oldAccounts) {
    const del = await request('DELETE', `${baseUrl}/bot_status?mt5_account_id=eq.${acc}`);
    console.log(`   Deleted bot_status for ${acc}: ${del.status}`);
  }

  // 3. Clean up old grid_config entries
  console.log('\n3. Cleaning up old grid_config entries...');
  const del4 = await request('DELETE', `${baseUrl}/grid_config?mt5_account_id=eq.474194522`);
  console.log(`   Deleted grid_config for 474194522: ${del4.status}`);

  // 4. Verify cleanup
  console.log('\n4. Verifying cleanup...');
  const balances = await new Promise((resolve, reject) => {
    https.get(`${baseUrl}/account_balance?select=user_id,balance`, {
      headers: { 'apikey': serviceKey, 'Authorization': 'Bearer ' + serviceKey }
    }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });
  console.log(`   Remaining balances: ${balances.length}`);

  const botStatus = await new Promise((resolve, reject) => {
    https.get(`${baseUrl}/bot_status?select=mt5_account_id,bot_active`, {
      headers: { 'apikey': serviceKey, 'Authorization': 'Bearer ' + serviceKey }
    }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });
  console.log(`   Remaining bot_status: ${botStatus.length}`);
  botStatus.forEach(b => console.log(`     ${b.mt5_account_id}: ${b.bot_active}`));

  console.log('\n=== Done ===');
  console.log('Now restart the bridge to sync correct balances.');
}

main().catch(console.error);
