import https from 'node:https';
import http from 'node:http';
import tls from 'node:tls';
import { fileURLToPath } from 'node:url';
import { createTunneledConnection } from '../tunnel.js';

/**
 * HTTP CONNECT proxy for all MCP traffic. Read from environment so the client
 * works behind a local proxy (Clash etc.) where direct outbound is blocked —
 * without this, a machine that can only reach the internet via a proxy gets
 * ECONNRESET on every request.
 */
const PROXY_URL =
  process.env.MCP_PROXY || process.env.HTTPS_PROXY || process.env.https_proxy || '';
const PROXY_TIMEOUT_MS = 30_000;

/**
 * Represents a JSON-RPC 2.0 Request object.
 * @see https://www.jsonrpc.org/specification
 */
interface JsonRpcRequest {
  jsonrpc: '2.0';
  id?: number | string;
  method: string;
  params?: Record<string, unknown> | unknown[];
}

/**
 * Result structure for MCP initialization.
 */
interface InitializeResult {
  protocolVersion: string;
  capabilities: Record<string, unknown>;
  serverInfo: {
    name: string;
    version: string;
  };
  [key: string]: unknown;
}

/**
 * Result structure for MCP tools list.
 */
interface ListToolsResult {
  tools: Array<{
    name: string;
    description?: string;
    inputSchema: Record<string, unknown>;
  }>;
  [key: string]: unknown;
}

/**
 * Represents a JSON-RPC 2.0 Response object.
 */
interface JsonRpcResponse<T = unknown> {
  jsonrpc: '2.0';
  id?: number | string;
  result?: T;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/**
 * Result structure for an MCP tool call.
 */
interface CallToolResult {
  content: Array<{
    type: string;
    text?: string;
    [key: string]: unknown;
  }>;
  isError?: boolean;
  [key: string]: unknown;
}

/**
 * MCP (Model Context Protocol) Client - Zero-Dependency Implementation
 * 
 * This client implements the "Streamable HTTP" transport protocol, which is 
 * increasingly used by modern MCP servers like DeepWiki.
 * 
 * It follows the JSON-RPC 2.0 specification for all communications.
 */
class McpClient {
  private readonly serverUrl: string;
  private requestId = 0;

  /**
   * Creates a new MCP Client.
   * @param serverUrl The endpoint of the MCP server (e.g., https://mcp.example.com/mcp)
   */
  constructor(serverUrl: string) {
    this.serverUrl = serverUrl;
  }

  /**
   * Sends a JSON-RPC request and waits for the response in the SSE stream.
   * 
   * @template T The expected type of the result
   * @param method The JSON-RPC method to call
   * @param params Parameters for the method
   * @returns A promise resolving to the method result
   * @throws Error if HTTP request fails or MCP returns an error
   */
  async request<T = unknown>(method: string, params: Record<string, unknown> | unknown[] = {}): Promise<T> {
    const id = ++this.requestId;
    const payload = JSON.stringify({
      jsonrpc: '2.0',
      id,
      method,
      params,
    } satisfies JsonRpcRequest);

    return new Promise((resolve, reject) => {
      const url = new URL(this.serverUrl);
      const isHttps = url.protocol === 'https:';
      const transport = isHttps ? https : http;

      const options: http.RequestOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream, application/json',
          'User-Agent': 'mcp-client-ts/1.0.0',
          'Content-Length': Buffer.byteLength(payload),
        },
      };

      const send = (createConnection?: () => tls.TLSSocket) => {
        const req = transport.request(
          this.serverUrl,
          { ...options, ...(createConnection ? { createConnection } : {}) },
          (res) => {
            if (res.statusCode && res.statusCode >= 400) {
              reject(new Error(`HTTP Error ${res.statusCode}: ${res.statusMessage}`));
              return;
            }

            let buffer = '';
            let rawBuffer = '';
            let eventData = '';
            let resolved = false;

            res.on('error', (err) => {
              if (!resolved) {
                resolved = true;
                reject(err);
              }
            });

            res.on('data', (chunk: Buffer | string) => {
              const chunkStr = chunk.toString();
              buffer += chunkStr;
              rawBuffer += chunkStr;

              // Parse SSE stream lines
              const lines = buffer.split('\n');
              buffer = lines.pop() ?? ''; // Keep partial line in buffer

              for (const line of lines) {
                const trimmed = line.trim();

                if (trimmed === '') {
                  // Empty line indicates the end of an event
                  if (eventData) {
                    try {
                      const msg = JSON.parse(eventData) as JsonRpcResponse<T>;
                      if (msg.id === id) {
                        resolved = true;
                        res.destroy(); // Prevent memory/socket leak
                        if (msg.error) {
                          reject(new Error(`MCP Error ${msg.error.code}: ${msg.error.message}`));
                        } else {
                          resolve(msg.result as T);
                        }
                      }
                    } catch {
                      // Ignore parse errors for heartbeats or invalid JSON
                    }
                    eventData = ''; // Reset for the next event
                  }
                } else if (trimmed.startsWith('data:')) {
                  // Accumulate data, preserving inner whitespace/newlines
                  eventData += line.substring(5).trim() + '\n';
                }
              }
            });

            res.on('end', () => {
              if (!resolved) {
                // Fallback for non-SSE JSON responses
                try {
                  const msg = JSON.parse(rawBuffer) as JsonRpcResponse<T>;
                  if (msg.id === id) {
                    if (msg.error) reject(new Error(msg.error.message));
                    else resolve(msg.result as T);
                  } else {
                    reject(new Error('Connection closed without receiving response matching request ID.'));
                  }
                } catch {
                  reject(new Error('Connection closed without receiving valid JSON-RPC response.'));
                }
              }
            });
          },
        );

        req.on('error', (err) => reject(err));
        req.write(payload);
        req.end();
      };

      if (isHttps && PROXY_URL) {
        createTunneledConnection(url, PROXY_URL, PROXY_TIMEOUT_MS)
          .then((createConnection) => send(createConnection))
          .catch((err) => reject(err));
      } else {
        send();
      }
    });
  }

  /**
   * Sends a JSON-RPC notification (no response expected).
   * 
   * @param method The JSON-RPC method to notify
   * @param params Parameters for the method
   */
  async notify(method: string, params: Record<string, unknown> | unknown[] = {}): Promise<void> {
    const payload = JSON.stringify({
      jsonrpc: '2.0',
      method,
      params,
    } satisfies JsonRpcRequest);

    return new Promise((resolve, reject) => {
      const url = new URL(this.serverUrl);
      const isHttps = url.protocol === 'https:';
      const transport = isHttps ? https : http;

      const options: http.RequestOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream, application/json',
          'User-Agent': 'mcp-client-ts/1.0.0',
          'Content-Length': Buffer.byteLength(payload),
        },
      };

      const send = (createConnection?: () => tls.TLSSocket) => {
        const req = transport.request(
          this.serverUrl,
          { ...options, ...(createConnection ? { createConnection } : {}) },
          (res) => {
            // We don't care about the response body for notifications, but we must consume it
            res.resume();
            if (res.statusCode && res.statusCode >= 400) {
              reject(new Error(`Notification HTTP Error ${res.statusCode}: ${res.statusMessage}`));
            } else {
              resolve();
            }
          },
        );

        req.on('error', (err) => reject(err));
        req.write(payload);
        req.end();
      };

      if (isHttps && PROXY_URL) {
        createTunneledConnection(url, PROXY_URL, PROXY_TIMEOUT_MS)
          .then((createConnection) => send(createConnection))
          .catch((err) => reject(err));
      } else {
        send();
      }
    });
  }

  /**
   * Initializes the MCP session with protocol-compliant capabilities.
   * @returns Initialization result including server info and capabilities
   */
  async initialize(): Promise<InitializeResult> {
    const result = await this.request<InitializeResult>('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'mcp-client-ts', version: '1.0.0' },
    });
    
    // Required by MCP protocol: send initialized notification after successful init
    await this.notify('notifications/initialized');
    
    return result;
  }

  /**
   * Lists all tools available on the MCP server.
   * @returns A list of tools with their names, descriptions, and input schemas
   */
  async listTools(): Promise<ListToolsResult> {
    return this.request<ListToolsResult>('tools/list');
  }

  /**
   * Calls a specific tool on the server.
   * 
   * @param name The unique name of the tool to call
   * @param args Arguments matching the tool's input schema
   * @returns The result of the tool execution
   */
  async callTool(name: string, args: Record<string, unknown>): Promise<CallToolResult> {
    return this.request<CallToolResult>('tools/call', {
      name,
      arguments: args,
    });
  }
}

// --- Main Execution (Test Case) ---

/**
 * Main execution function demonstrating MCP client usage.
 */
async function main(): Promise<void> {
  const config = {
    mcpServers: {
      deepwiki: {
        serverUrl: 'https://mcp.deepwiki.com/mcp',
      },
    },
  };

  const client = new McpClient(config.mcpServers.deepwiki.serverUrl);

  try {
    console.log('Connecting and initializing DeepWiki MCP...');
    await client.initialize();
    console.log('Initialized successfully.');

    console.log('Calling read_wiki_structure for Tencent/ncnn...');
    // Note: DeepWiki's read_wiki_structure tool uses "repoName" as the argument key.
    const result = await client.callTool('read_wiki_structure', {
      repoName: 'Tencent/ncnn',
    });

    console.log('\n=== Tencent/ncnn Structure ===');
    const firstContent = result.content[0];
    if (firstContent && 'text' in firstContent && typeof firstContent.text === 'string') {
      console.log(firstContent.text);
    } else {
      console.log(JSON.stringify(result, null, 2));
    }

  } catch (error) {
    console.error('\n!!! MCP Client Error !!!');
    if (error instanceof Error) {
      console.error(error.message);
    } else {
      console.error(String(error));
    }
  } finally {
    process.exit(0);
  }
}

// Check if running directly as the main script
const isMain = process.argv[1] && (
  process.argv[1] === fileURLToPath(import.meta.url) ||
  process.argv[1].endsWith('mcp-client.ts') ||
  process.argv[1].endsWith('mcp-client.js')
);

if (isMain) {
  main().catch((err) => {
    console.error('Fatal Error:', err);
    process.exit(1);
  });
}

export { McpClient, type JsonRpcRequest, type JsonRpcResponse, type CallToolResult, type InitializeResult, type ListToolsResult };
