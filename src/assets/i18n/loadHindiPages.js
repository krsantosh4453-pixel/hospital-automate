// Loads the Hindi page dictionary (hiPages.js, ~200 kB) on demand, so English
// users never download it. The result is cached: once loaded, it is available
// synchronously through getLoadedHindiPages() and Hindi renders without a flash.

let loadedPages = null
let pendingLoad = null

/** The Hindi page dictionary if it has already been loaded, otherwise null. */
export function getLoadedHindiPages() {
  return loadedPages
}

/** Loads the Hindi page dictionary once; a failed load can be retried. */
export function loadHindiPages() {
  if (loadedPages) return Promise.resolve(loadedPages)
  if (!pendingLoad) {
    pendingLoad = import("./hiPages.js")
      .then((module) => {
        loadedPages = module.default
        return loadedPages
      })
      .catch((error) => {
        pendingLoad = null
        throw error
      })
  }
  return pendingLoad
}
