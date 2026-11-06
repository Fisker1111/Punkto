import { createMcpHandler } from 'agents/mcp/server';
import { McpServer } from '@modelcontextprotocol/server';
import { registerTools } from './tools.js';
export function createHandler() {
  return createMcpHandler(() => {
    const server = new McpServer({ name: 'punkto-mcp', version: '0.1.0' });
    registerTools(server);
    return server;
  }, { route: '/mcp', legacy: 'stateless', responseMode: 'auto' });
}

// Agents documents one handler per module, with a fresh server from the factory
// for every request (docs/mcp-servers.md and docs/mcp-transports.md).
export const handler = createHandler();
