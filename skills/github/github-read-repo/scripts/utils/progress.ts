/**
 * progress.ts — minimal elapsed-time progress reporting for long, blocking
 * network operations (MCP calls, multi-MB downloads, SSE waits) that otherwise
 * print nothing for tens of seconds and look hung.
 *
 * Everything goes to stderr so piped stdout stays clean. `timer.unref()` keeps
 * the ticker from holding the process open once the fetch completes.
 */

/** Format milliseconds as a compact elapsed string ("12.3s", "2m05s"). */
export function formatElapsed(ms: number): string {
  const totalSec = ms / 1000;
  if (totalSec < 60) return `${totalSec.toFixed(1)}s`;
  const m = Math.floor(totalSec / 60);
  const s = Math.floor(totalSec % 60);
  return `${m}m${String(s).padStart(2, "0")}s`;
}

/**
 * Start a periodic elapsed reporter for a blocking operation. Prints a line to
 * stderr every `intervalMs` ("[12.3s] <label>…"). Call the returned stop()
 * when the operation completes; it clears the timer and prints a done line.
 */
export function startElapsedReporter(label: string, intervalMs = 10_000): () => void {
  const started = Date.now();
  const timer = setInterval(() => {
    console.error(`[${formatElapsed(Date.now() - started)}] ${label}…`);
  }, intervalMs);
  // Don't keep the process alive just for the ticker.
  timer.unref?.();
  return () => {
    clearInterval(timer);
    console.error(`[${formatElapsed(Date.now() - started)}] ${label} 完成`);
  };
}
