const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';
const supabaseUrl = 'https://lakbvdmjtoarmxmzvynu.supabase.co';
const baseUrl = supabaseUrl + '/rest/v1';
const authUrl = supabaseUrl + '/auth/v1';

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
  console.log('=== Check existing users ===\n');

  // List all auth users
  const listUsers = await request('GET', `${authUrl}/admin/users`);
  console.log('Auth users response:', listUsers.status);
  
  try {
    const usersData = JSON.parse(listUsers.data);
    console.log(`Total users: ${usersData.users?.length || 0}`);
    usersData.users?.forEach((u, i) => {
      console.log(`  ${i+1}. ${u.email} (ID: ${u.id})`);
    });
  } catch (e) {
    console.log('Response:', listUsers.data);
  }

  // Try to find Karim's user
  console.log('\n=== Looking for Karim ===');
  const karimCheck = await request('GET', 
    `${authUrl}/admin/users?email=Karimmabdelmoneim@gmail.com`
  );
  console.log('Karim check:', karimCheck.status, karimCheck.data);
}

main().catch(console.error);
