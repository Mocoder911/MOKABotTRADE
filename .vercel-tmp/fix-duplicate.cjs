const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';

// Delete duplicate profile (keep admin user, remove the other)
const url = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1/profiles?id=eq.8b04ae08-7e7d-4d98-ae55-6aa17f113f83';
const options = {
  method: 'DELETE',
  headers: {
    'apikey': serviceKey,
    'Authorization': 'Bearer ' + serviceKey
  }
};

const req = https.request(url, options, (res) => {
  let data = '';
  res.on('data', chunk => data += chunk);
  res.on('end', () => {
    console.log('Delete status:', res.statusCode);
    console.log('Response:', data || '(empty)');
    
    // Now verify only one profile remains
    const verifyUrl = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1/profiles?select=id,email,mt5_account_id,status';
    const verifyOpts = {
      headers: {
        'apikey': serviceKey,
        'Authorization': 'Bearer ' + serviceKey
      }
    };
    https.get(verifyUrl, verifyOpts, (r2) => {
      let d2 = '';
      r2.on('data', c => d2 += c);
      r2.on('end', () => {
        console.log('\nRemaining profiles:', d2);
      });
    });
  });
});
req.on('error', e => console.error('Error:', e.message));
req.end();
