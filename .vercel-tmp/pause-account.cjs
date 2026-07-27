const https = require('https');
const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';
const url = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1/bot_status?mt5_account_id=eq.474202217';
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
  res.on('end', () => console.log(`Status: ${res.statusCode} — ${d}`));
});
req.on('error', e => console.error(e));
req.write(JSON.stringify({ bot_active: false }));
req.end();
