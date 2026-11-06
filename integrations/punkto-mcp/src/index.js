import { createHandler } from './handler.js';
export default {
  async fetch(request, env, ctx) {
    if (new URL(request.url).pathname !== '/mcp') return Response.json({ error: 'not_found' }, { status: 404 });
    if (request.method !== 'POST') return Response.json({ error: 'method_not_allowed' }, { status: 405 });
    return createHandler()(request, env, ctx);
  },
};
