/**
 * tunnel.ts — HTTP CONNECT proxy tunneling for https.request.
 *
 * A local proxy (Clash / ClashX / V2Ray mixed port) exposes an HTTP CONNECT
 * endpoint. After the CONNECT handshake the socket is a raw TCP stream; for
 * TLS targets Node does NOT wrap custom createConnection sockets automatically,
 * so the TLS handshake must be performed explicitly with tls.connect — the
 * tunnel only carries the CONNECT phase. Without this, the plaintext HTTP
 * request line is sent straight to the :443 port and the server answers
 * "400 plain HTTP request was sent to HTTPS port".
 *
 * Exported for every API-cache crawler (gitingest / gitdiagram) and the
 * DeepWiki MCP client so all outbound HTTPS honors HTTPS_PROXY consistently.
 */

import net from "node:net";
import tls from "node:tls";

/**
 * Establish a CONNECT tunnel through `proxyUrl` to `target`, returning a
 * createConnection factory that yields an already-TLS-wrapped socket.
 *
 * The returned factory is only handed to https.request after the TLS handshake
 * completes, so the request is never sent on a half-open tunnel.
 *
 * @param target The final HTTPS target URL.
 * @param proxyUrl HTTP CONNECT proxy (http://host:port).
 * @param timeoutMs Per-phase timeout (connect / CONNECT / TLS handshake).
 * @returns A function suitable for `https.request` `createConnection`.
 */
export function createTunneledConnection(
  target: URL,
  proxyUrl: string,
  timeoutMs: number,
): Promise<() => tls.TLSSocket> {
  return new Promise((resolve, reject) => {
    const pu = new URL(proxyUrl);
    const socket = net.connect({ host: pu.hostname, port: Number(pu.port) || 443 });
    socket.setTimeout(timeoutMs);
    socket.on("connect", () => {
      socket.write(
        `CONNECT ${target.hostname}:${target.port || 443} HTTP/1.1\r\n` +
          `Host: ${target.hostname}:${target.port || 443}\r\n\r\n`,
      );
    });
    let head = "";
    const onData = (chunk: Buffer) => {
      head += chunk.toString("latin1");
      if (!head.includes("\r\n\r\n")) return;
      socket.removeListener("data", onData);
      const m = head.match(/^HTTP\/\d(?:\.\d)? (\d{3})/);
      if (m && m[1] === "200") {
        // CONNECT phase done; timeout ownership moves to the TLS socket.
        socket.setTimeout(0);
        const tlsSocket = tls.connect({
          socket,
          servername: target.hostname,
          ALPNProtocols: ["http/1.1"],
        });
        tlsSocket.setTimeout(timeoutMs);
        tlsSocket.on("timeout", () => {
          tlsSocket.destroy();
          reject(new Error(`TLS handshake timeout after ${timeoutMs}ms: ${target.hostname}`));
        });
        tlsSocket.on("error", reject);
        tlsSocket.on("secureConnect", () => resolve(() => tlsSocket));
      } else {
        socket.destroy();
        reject(new Error(`proxy CONNECT failed: ${m ? m[1] : head.split("\r\n")[0]}`));
      }
    };
    socket.on("data", onData);
    socket.on("timeout", () => {
      socket.destroy();
      reject(new Error(`proxy connect timeout: ${proxyUrl}`));
    });
    socket.on("error", reject);
  });
}
