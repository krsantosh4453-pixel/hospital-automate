// Code 39 barcode encoding for sample labels (requirement F6). Code 39 is
// read by every common USB/handheld scanner and needs no check digit.
// Each character is 9 elements (bar, space, bar, …): n = narrow, w = wide.

const PATTERNS = {
  "0": "nnnwwnwnn", "1": "wnnwnnnnw", "2": "nnwwnnnnw", "3": "wnwwnnnnn", "4": "nnnwwnnnw",
  "5": "wnnwwnnnn", "6": "nnwwwnnnn", "7": "nnnwnnwnw", "8": "wnnwnnwnn", "9": "nnwwnnwnn",
  A: "wnnnnwnnw", B: "nnwnnwnnw", C: "wnwnnwnnn", D: "nnnnwwnnw", E: "wnnnwwnnn",
  F: "nnwnwwnnn", G: "nnnnnwwnw", H: "wnnnnwwnn", I: "nnwnnwwnn", J: "nnnnwwwnn",
  K: "wnnnnnnww", L: "nnwnnnnww", M: "wnwnnnnwn", N: "nnnnwnnww", O: "wnnnwnnwn",
  P: "nnwnwnnwn", Q: "nnnnnnwww", R: "wnnnnnwwn", S: "nnwnnnwwn", T: "nnnnwnwwn",
  U: "wwnnnnnnw", V: "nwwnnnnnw", W: "wwwnnnnnn", X: "nwnnwnnnw", Y: "wwnnwnnnn",
  Z: "nwwnwnnnn", "-": "nwnnnnwnw", ".": "wwnnnnwnn", " ": "nwwnnnwnn", "*": "nwnnwnwnn",
}

export const NARROW = 1
export const WIDE = 3

/** True when every character can be printed as Code 39. */
export function canEncode(text) {
  return [...String(text).toUpperCase()].every((ch) => ch !== "*" && ch in PATTERNS)
}

/**
 * Bars of the Code 39 symbol for ``text`` (start/stop "*" added), as
 * [{ x, width }] in narrow-module units, plus the total width.
 * @param {string} text
 * @returns {{ bars: { x: number, width: number }[], width: number }}
 */
export function code39Bars(text) {
  const value = String(text).toUpperCase()
  if (!canEncode(value)) throw new Error(`Cannot encode "${text}" as Code 39`)
  const bars = []
  let x = 0
  for (const ch of `*${value}*`) {
    ;[...PATTERNS[ch]].forEach((element, i) => {
      const width = element === "w" ? WIDE : NARROW
      if (i % 2 === 0) bars.push({ x, width })
      x += width
    })
    x += NARROW // gap between characters
  }
  return { bars, width: x - NARROW }
}
