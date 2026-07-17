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
  const LOGIN = '256711835';
  const SERVER = 'Exness-MT5Real35';
  const PASSWORD = 'Kikokok3@';

  // 1. profiles — need to find the admin user_id first
  console.log('=== Adding Real Account 256711835 ===\n');

  // Get admin user_id
  const profileUrl = `${baseUrl}/profiles?select=id,email&email=eq.mo.salamah911@gmail.com&limit=1`;
  const profileRes = await new Promise((resolve, reject) => {
    https.get(profileUrl, {
      headers: { 'apikey': serviceKey, 'Authorization': 'Bearer ' + serviceKey }
    }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });

  const userId = profileRes[0]?.id;
  console.log(`Admin user_id: ${userId}`);

  // 2. bot_status
  console.log('\nAdding bot_status...');
  const bs = await post('bot_status', { mt5_account_id: LOGIN, bot_active: true });
  console.log(`bot_status: ${bs.status} — ${bs.data}`);

  // 3. grid_config (Lot=0.02, Basket=$10)
  console.log('\nAdding grid_config (Lot=0.02, Step=500, Max=10, Basket=$10)...');
  const gc = await post('grid_config', {
    mt5_account_id: LOGIN,
    lot_size: 0.02,
    grid_step: 500,
    max_orders: 10,
    basket_profit: 10.0
  });
  console.log(`grid_config: ${gc.status} — ${gc.data}`);

  console.log('\n=== Summary ===');
  console.log(`Account: ${LOGIN}`);
  console.log(`Server: ${SERVER}`);
  console.log(`Lot: 0.02 | Step: 500 | Max: 10 | Basket: $10`);
  console.log(`Bot Active: true`);
}

main().catch(console.error);
