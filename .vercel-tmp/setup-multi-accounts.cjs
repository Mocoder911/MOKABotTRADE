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
  console.log('=== Multi-Account Setup ===\n');

  // 1. Update existing profile (474202217) with new password
  console.log('1. Updating profile 474202217 (mo.salamah911@gmail.com)...');
  const update1 = await request('PATCH', 
    `${baseUrl}/profiles?mt5_account_id=eq.474202217`,
    { mt5_password: 'M0hadm1n' }
  );
  console.log(`   Result: ${update1.status}`);

  // 2. Create new auth user for Karim
  console.log('\n2. Creating auth user Karimmabdelmoneim@gmail.com...');
  const createUser = await request('POST',
    `${authUrl}/admin/users`,
    {
      email: 'Karimmabdelmoneim@gmail.com',
      password: 'Kikokok3@',
      email_confirm: true
    }
  );
  console.log(`   Result: ${createUser.status}`);
  let karimUserId = null;
  try {
    const userData = JSON.parse(createUser.data);
    karimUserId = userData.id;
    console.log(`   User ID: ${karimUserId}`);
  } catch (e) {
    console.log(`   Response: ${createUser.data}`);
  }

  // 3. Create profile for Karim with MT5 account 256711835
  if (karimUserId) {
    console.log('\n3. Creating profile for Karim (MT5: 256711835)...');
    const createProfile = await request('POST',
      `${baseUrl}/profiles`,
      {
        id: karimUserId,
        email: 'Karimmabdelmoneim@gmail.com',
        full_name: 'Karim',
        role: 'user',
        status: 'active',
        mt5_account_id: '256711835',
        mt5_server: 'Exness-MT5Real35',
        mt5_password: 'Kikokok3@',
        verification_status: 'VALIDATED'
      }
    );
    console.log(`   Result: ${createProfile.status}`);
  }

  // 4. Verify profiles
  console.log('\n4. Verifying profiles...');
  const verify = await request('GET',
    `${baseUrl}/profiles?select=id,email,mt5_account_id,mt5_server,mt5_password,status`
  );
  const profiles = JSON.parse(verify.data);
  console.log(`   Total profiles: ${profiles.length}`);
  profiles.forEach((p, i) => {
    console.log(`   ${i+1}. ${p.email} → MT5: ${p.mt5_account_id} (${p.mt5_server})`);
  });

  console.log('\n=== Done ===');
  console.log('Accounts ready:');
  console.log('  • 474202217 (mo.salamah911@gmail.com) - Trial');
  console.log('  • 256711835 (Karimmabdelmoneim@gmail.com) - Real');
}

main().catch(console.error);
