module.exports = {
  apps: [
    {
      name: 'moka-web',
      script: 'node_modules/next/dist/bin/next',
      args: 'start -p 80',
      cwd: 'C:\\Users\\Administrator\\Desktop\\MokaBotTrade',
      env: {
        NODE_ENV: 'production',
        PORT: 80,
      },
      instances: 1,
      autorestart: true,
      max_memory_restart: '500M',
    },
  ],
};
