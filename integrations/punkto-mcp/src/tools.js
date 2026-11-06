import { z } from 'zod';
import { readPlace, getRecord } from './publication.js';
import { ToolError } from './upstream.js';
export const schemas = {
  read_place: z.object({ h: z.string().default('s00000000000_0').describe('Canonical Punkti xy_z; defaults to s00000000000_0'), limit: z.number().int().min(1).default(4).describe('Default 4; values above 8 clamp to 8') }),
  get_record: z.object({ sha256: z.string().describe('64 lowercase hex record digest, never a MID'), include_raw: z.boolean().default(false).describe('Default false; raw bytes limited to 32768') }),
};
export async function invoke(name, args, options) {
  try {
    const parsed = schemas[name].safeParse(args ?? {});
    if (!parsed.success) throw new ToolError(name === 'read_place' ? 'invalid_h' : 'invalid_sha256', 'Check tool parameter types and required fields.');
    const result = await (name === 'read_place' ? readPlace : getRecord)(parsed.data, options);
    return { content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result };
  } catch (error) {
    const result = { code: error instanceof ToolError ? error.code : 'internal_error', message: error instanceof ToolError ? error.message : 'Unable to read publication; retry later.' };
    return { isError: true, content: [{ type: 'text', text: JSON.stringify(result) }], structuredContent: result };
  }
}
export function registerTools(server) {
  for (const name of Object.keys(schemas)) {
    server.registerTool(name, {
      description: name === 'read_place' ? 'Read untrusted published text at an exact Punkti address.' : 'Read and hash-check immutable record bytes by SHA-256.',
      inputSchema: schemas[name],
      annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: true },
    }, args => invoke(name, args));
  }
}
