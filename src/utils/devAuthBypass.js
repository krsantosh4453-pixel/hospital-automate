// The development sign-in bypass signs anyone opening the dev server in as a
// fake Admin. It is never available in a production build, and in development
// only when VITE_DEV_AUTH_BYPASS is explicitly "true".
export function isDevelopmentAuthBypassEnabled(env = import.meta.env) {
  if (!env.DEV || env.PROD) {
    return false
  }
  return String(env.VITE_DEV_AUTH_BYPASS ?? "").trim().toLowerCase() === "true"
}
