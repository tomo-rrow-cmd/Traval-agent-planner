/**
 * Vitest setup — localStorage polyfill for Node.js v22+/v26+
 *
 * Node.js v22.14+ reserves globalThis.localStorage but sets it to undefined
 * (the experimental API requires --localstorage-file). This prevents happy-dom
 * from providing its own implementation.
 */
const rawGlobal = globalThis as Record<string, unknown>

if (typeof rawGlobal.localStorage === 'undefined' || rawGlobal.localStorage === null) {
  const store: Map<string, string> = new Map()
  Object.defineProperty(globalThis, 'localStorage', {
    value: {
      getItem: (k: string): string | null => store.get(k) ?? null,
      setItem: (k: string, v: string) => { store.set(k, String(v)) },
      removeItem: (k: string) => { store.delete(k) },
      clear: () => { store.clear() },
      get length(): number { return store.size },
      key: (i: number): string | null => [...store.keys()][i] ?? null,
    },
    writable: true,
    configurable: true,
  })
}
