const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';

// Insert profile for admin user with new MT5 account
const body = JSON.stringify({
  id: '41e69c7f-f87a-4b40-9b87-bd675b384b9d',
  email: 'mo.salamah911@gmail.com',
  full_name: 'Mo Salamah',
  role: 'admin',
  status: 'active',
  mt5_account_id: '474194522',
  mt5_password: 'Kikokok3@',
  mt5_server: 'Exness-MT5Trial15',
  bot_active: true,
  verification_status: 'VALIDATED'
});

const url = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1/profiles';
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
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    console.log('Status:', res.statusCode);
    console.log('Response:', data);
  });
});
req.on('error', e => console.error('Error:', e.message));
req.write(body);
req.end();
