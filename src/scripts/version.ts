declare const __BUILD_ID__: string;

/** Appends the build id to a data URL, so every deploy asks the cache for a fresh copy instead of reusing one up to an hour old. */
export function versioned(url: string): string {
  const id = typeof __BUILD_ID__ === 'undefined' ? 'dev' : __BUILD_ID__;
  return `${url}${url.includes('?') ? '&' : '?'}v=${id}`;
}
