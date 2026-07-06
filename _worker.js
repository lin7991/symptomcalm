// SymptomCalm Newsletter Subscription Worker
// Deploy to Cloudflare Workers at /api/subscribe route

// KV namespace binding: symptomcalm-subscribers
// (Configure in Cloudflare Dashboard: Workers → your worker → KV)

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  // Handle CORS preflight
  if (request.method === 'OPTIONS') {
    return event.respondWith(new Response(null, {
      status: 204,
      headers: CORS_HEADERS,
    }));
  }

  // Only handle POST to /api/subscribe
  if (request.method !== 'POST' || url.pathname !== '/api/subscribe') {
    return event.respondWith(new Response('Not found', {
      status: 404,
      headers: CORS_HEADERS,
    }));
  }

  event.respondWith(handleSubscribe(request));
});

async function handleSubscribe(request) {
  try {
    const body = await request.json();
    const email = (body.email || '').trim().toLowerCase();

    // Validate email
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return jsonResponse({ ok: false, error: 'Invalid email address' }, 400);
    }

    // Check if already subscribed
    const existing = await SUBSCRIBERS.get(email);
    if (existing) {
      return jsonResponse({ ok: true, message: 'Already subscribed' });
    }

    // Store subscriber
    await SUBSCRIBERS.put(email, JSON.stringify({
      email: email,
      subscribed_at: new Date().toISOString(),
      source: 'symptomcalm',
    }));

    return jsonResponse({ ok: true, message: 'Subscription successful' });
  } catch (err) {
    return jsonResponse({ ok: false, error: 'Internal error' }, 500);
  }
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status: status,
    headers: {
      'Content-Type': 'application/json',
      ...CORS_HEADERS,
    },
  });
}
