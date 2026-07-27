const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';
const baseUrl = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1';

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
  // Add bot_status for first account
  console.log('Adding bot_status for 474194522...');
  const bs = await post('bot_status', { mt5_account_id: '474194522', bot_active: true });
  console.log('bot_status:', bs.status, bs.data);

  // Add grid_config for first account
  console.log('\nAdding grid_config for 474194522...');
  const gc = await post('grid_config', { mt5_account_id: '474194522', lot_size: 0.07, grid_step: 500, max_orders: 10, basket_profit: 20.0 });
  console.log('grid_config:', gc.status, gc.data);

  console.log('\nDone! Now you can run both accounts:');
  console.log('  Terminal 1: python mt5_bridge.py 474194522');
  console.log('  Terminal 2: python mt5_bridge.py 474202217');
}

main().catch(console.error);
