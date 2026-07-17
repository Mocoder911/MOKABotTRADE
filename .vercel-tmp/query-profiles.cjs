const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';

// Query profiles with service role key
const url = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1/profiles?select=*';
const options = {
  headers: {
    'apikey': serviceKey,
    'Authorization': 'Bearer ' + serviceKey
  }
};

https.get(url, options, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    console.log('Status:', res.statusCode);
    const profiles = JSON.parse(data);
    profiles.forEach(p => {
      console.log(`\nProfile:`);
      console.log(`  id: ${p.id}`);
      console.log(`  email: ${p.email}`);
      console.log(`  role: ${p.role}`);
      console.log(`  status: ${p.status}`);
      console.log(`  mt5_account_id: ${p.mt5_account_id}`);
      console.log(`  mt5_server: ${p.mt5_server}`);
      console.log(`  mt5_password: ${p.mt5_password ? '***' : 'NULL'}`);
      console.log(`  bot_active: ${p.bot_active}`);
      console.log(`  verification_status: ${p.verification_status}`);
    });
  });
}).on('error', e => console.error('Error:', e.message));
