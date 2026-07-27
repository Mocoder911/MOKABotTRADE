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
  console.log('=== Setup Karim Profile ===\n');

  const KARIM_USER_ID = '58a3b12f-5dac-47f9-99f9-973cfd2f8ad9';
  const KARIM_EMAIL = 'karimmabdelmoneim@gmail.com';
  const MT5_LOGIN = '256711835';
  const MT5_SERVER = 'Exness-MT5Real35';
  const MT5_PASSWORD = 'Kikokok3@';

  // 1. Update Karim's user_metadata with new MT5 credentials
  console.log('1. Updating Karim user_metadata...');
  const updateMeta = await request('PUT',
    `${authUrl}/admin/users/${KARIM_USER_ID}`,
    {
      user_metadata: {
        email_verified: true,
        full_name: 'Karim',
        mt5_account_id: MT5_LOGIN,
        mt5_password: MT5_PASSWORD,
        mt5_server: MT5_SERVER
      }
    }
  );
  console.log(`   Result: ${updateMeta.status}`);

  // 2. Create profile for Karim
  console.log('\n2. Creating profile for Karim...');
  const createProfile = await request('POST',
    `${baseUrl}/profiles`,
    {
      id: KARIM_USER_ID,
      email: KARIM_EMAIL,
      full_name: 'Karim',
      role: 'user',
      status: 'active',
      mt5_account_id: MT5_LOGIN,
      mt5_server: MT5_SERVER,
      mt5_password: MT5_PASSWORD,
      verification_status: 'VALIDATED'
    }
  );
  console.log(`   Result: ${createProfile.status}`);
  if (createProfile.status !== 201) {
    console.log(`   Response: ${createProfile.data}`);
  }

  // 3. Delete lovelyfish profile if exists (old duplicate)
  console.log('\n3. Cleaning up old profiles...');
  const LOVELYFISH_ID = '8b04ae08-7e7d-4d98-ae55-6aa17f113f83';
  const deleteOld = await request('DELETE',
    `${baseUrl}/profiles?id=eq.${LOVELYFISH_ID}`
  );
  console.log(`   Deleted lovelyfish profile: ${deleteOld.status}`);

  // 4. Verify all profiles
  console.log('\n4. Verifying profiles...');
  const verify = await request('GET',
    `${baseUrl}/profiles?select=id,email,mt5_account_id,mt5_server,status&order=email`
  );
  const profiles = JSON.parse(verify.data);
  console.log(`   Total profiles: ${profiles.length}`);
  profiles.forEach((p, i) => {
    console.log(`   ${i+1}. ${p.email} → MT5: ${p.mt5_account_id} (${p.mt5_server}) [${p.status}]`);
  });

  console.log('\n=== Done ===');
}

main().catch(console.error);
