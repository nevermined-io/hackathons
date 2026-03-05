// Patch the paid-endpoint.js to forward prompts to the local OpenClaw agent
// instead of using the mock weather handler.
const fs = require('fs');
const path = '/root/.openclaw/extensions/openclaw-plugin/dist/paid-endpoint.js';
let src = fs.readFileSync(path, 'utf8');

// 1. Fix route auth
src = src.replace(
  'api.registerHttpRoute({ path, handler: routeHandler })',
  'api.registerHttpRoute({ path, handler: routeHandler, auth: "plugin" })'
);

// 2. Replace mock handler with local OpenAI-compatible chat completions call
src = src.replace(
  'const handler = agentHandler ?? mockWeatherHandler;',
  `const handler = agentHandler ?? async function localAgentHandler({ prompt }) {
    const http = require('http');
    const token = 'demo';
    const postData = JSON.stringify({
      model: 'openai/gpt-4o-mini',
      messages: [{ role: 'user', content: prompt }],
    });
    return new Promise((resolve, reject) => {
      const req = http.request({
        hostname: '127.0.0.1',
        port: 18789,
        path: '/v1/chat/completions',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token,
          'Content-Length': Buffer.byteLength(postData),
        },
      }, (res) => {
        let body = '';
        res.on('data', (chunk) => { body += chunk; });
        res.on('end', () => {
          try {
            const parsed = JSON.parse(body);
            const text = parsed.choices?.[0]?.message?.content || body;
            resolve({ response: text });
          } catch {
            resolve({ response: body || 'No response' });
          }
        });
      });
      req.on('error', reject);
      req.write(postData);
      req.end();
      setTimeout(() => { req.destroy(); resolve({ response: 'Timeout' }); }, 60000);
    });
  };`
);

fs.writeFileSync(path, src);
console.log('Patched paid-endpoint.js: local agent handler + route auth');
