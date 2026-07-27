const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';
const baseUrl = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1';

function get(url) {
  return new Promise((resolve, reject) => {
    https.get(url, {
      headers: { 'apikey': serviceKey, 'Authorization': 'Bearer ' + serviceKey }
    }, (res) => {
      let d = '';
      res.on('data', c => d += c);
      res.on('end', () => resolve(JSON.parse(d)));
    }).on('error', reject);
  });
}

async function main() {
  console.log('=== Check Data Consistency ===\n');

  // 1. Check profiles
  console.log('1. Profiles:');
  const profiles = await get(`${baseUrl}/profiles?select=id,email,mt5_account_id,mt5_server`);
  profiles.forEach(p => {
    console.log(`   ${p.email} → MT5: ${p.mt5_account_id} (${p.mt5_server})`);
  });

  // 2. Check account_balance
  console.log('\n2. Account Balance:');
  const balances = await get(`${baseUrl}/account_balance?select=user_id,balance,equity,updated_at`);
  balances.forEach(b => {
    console.log(`   User: ${b.user_id} | Balance: $${b.balance} | Equity: $${b.equity}`);
  });

  // 3. Check bot_status
  console.log('\n3. Bot Status:');
  const botStatus = await get(`${baseUrl}/bot_status?select=mt5_account_id,bot_active`);
  botStatus.forEach(b => {
    console.log(`   Account: ${b.mt5_account_id} | Active: ${b.bot_active}`);
  });

  // 4. Check grid_config
  console.log('\n4. Grid Config:');
  const configs = await get(`${baseUrl}/grid_config?select=mt5_account_id,lot_size,basket_profit`);
  configs.forEach(c => {
    console.log(`   Account: ${c.mt5_account_id} | Lot: ${c.lot_size} | Basket: $${c.basket_profit}`);
  });

  // 5. Check trades by account
  console.log('\n5. Trades by account:');
  const trades = await get(`${baseUrl}/trades?select=account_id,symbol,status&limit=5`);
  trades.forEach(t => {
    console.log(`   Account: ${t.account_id} | ${t.symbol} | ${t.status}`);
  });
}

main().catch(console.error);
