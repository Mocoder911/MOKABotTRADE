const https = require('https');

const serviceKey = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxha2J2ZG1qdG9hcm14bXp2eW51Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjkwMzA2NywiZXhwIjoyMDk4NDc5MDY3fQ.Y92Hm4kDpOVlOFZsRUkqlbuk3P4z7m-e3DARjtoqtvE';

const url = 'https://lakbvdmjtoarmxmzvynu.supabase.co/rest/v1/trades?select=ticket,symbol,type,volume,entry,live_pl,status,open_time&account_id=eq.474202217&status=eq.open&order=open_time.desc&limit=30';
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
    const trades = JSON.parse(data);
    console.log(`\nTotal open trades: ${trades.length}\n`);
    trades.forEach((t, i) => {
      console.log(`${i+1}. ${t.symbol} | ${t.type} | Vol: ${t.volume} | Entry: ${t.entry} | P/L: $${t.live_pl?.toFixed(2)} | Ticket: ${t.ticket}`);
    });
  });
}).on('error', e => console.error('Error:', e.message));
