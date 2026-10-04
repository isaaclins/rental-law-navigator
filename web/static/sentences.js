// Sentence splitting for rule summaries (#163). A classic script (loaded before app.js) so tests can run it in Node.
// A sentence ends at . ! ? followed by whitespace, never inside a number ("1.6%", "$68.96", "1.5 times"), after a
// known abbreviation ("U.S.", "Sec.", "et seq.", "Cal.", "No.") or inside parentheses/brackets.
(function (root) {
  const ABBR = new Set(["u.s", "sec", "secs", "seq", "et seq", "cal", "civ", "gov", "mun", "admin", "ord", "ords", "no", "nos", "inc", "st", "ave",
    "blvd", "rd", "mr", "mrs", "ms", "dr", "vs", "v", "e.g", "i.e", "etc", "art", "ch", "para", "subd", "approx", "jan", "feb", "mar", "apr", "jun",
    "jul", "aug", "sept", "sep", "oct", "nov", "dec", "p.l", "c", "n.j.s.a", "n.j.a.c", "m.g.l", "g.l", "l.a", "s.f", "a.b", "s.b", "h.r", "art", "núm", "art", "pág"]);
  function splitSentences(text) {
    const s = String(text ?? "");
    const out = [];
    let depth = 0, start = 0;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (c === "(" || c === "[") depth++;
      else if ((c === ")" || c === "]") && depth > 0) depth--;
      else if ((c === "." || c === "!" || c === "?") && depth === 0) {
        let j = i + 1;
        while (j < s.length && /["”’)\]]/.test(s[j])) j++; // closing quotes stay with the sentence
        if (j < s.length && !/\s/.test(s[j])) continue; // "1.6", "U.S.C", "e.g.,"
        if (c === ".") {
          const before = s.slice(start, i).match(/([A-Za-zÁÉÍÓÚáéíóúñÑ.]+(?: seq)?)$/);
          const word = before ? before[1].toLowerCase() : "";
          if (ABBR.has(word) || ABBR.has(word.replace(/^.*\s/, "")) || /^[a-z]$/i.test(word) || /(^|\.)[a-z]\.[a-z]$/i.test(word)) continue;
        }
        let k = j;
        while (k < s.length && /\s/.test(s[k])) k++;
        if (k < s.length && /[a-z]/.test(s[k])) continue; // next word in lower case: not a sentence start
        out.push(s.slice(start, j).trim());
        start = k;
        i = k - 1;
      }
    }
    const rest = s.slice(start).trim();
    if (rest) out.push(rest);
    return out.filter(Boolean);
  }
  root.CE_TEXT = Object.freeze({ splitSentences });
})(typeof window !== "undefined" ? window : globalThis);

// "New rent" field of Check a rent increase: an amount ("2300", "$2,300"), a percentage ("5%", "+5%"), or a change
// ("+300", "300 more", "+$300", "-100"). A signed or "more"/"less" value is relative to the current rent.
(function (root) {
  function parseNewRent(text, current) {
    const s = String(text ?? "").trim().toLowerCase();
    if (!s) return null;
    const n = parseFloat(s.replace(/[^0-9.]/g, ""));
    if (!Number.isFinite(n)) return null;
    const minus = /^-|\b(less|menos)\b/.test(s), plus = /^\+|\b(more|extra|más|mas)\b/.test(s);
    if (/%/.test(s)) return { increase_pct: minus ? -n : n };
    if (plus || minus) return current ? { new_rent: Math.round((current + (minus ? -n : n)) * 100) / 100, delta: minus ? -n : n } : null;
    return { new_rent: n };
  }
  root.CE_RENT = { parseNewRent };
})(typeof window !== "undefined" ? window : globalThis);
