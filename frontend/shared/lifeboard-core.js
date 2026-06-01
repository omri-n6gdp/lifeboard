/* Lifeboard shared data layer.
   Every design imports this; it knows how to talk to /api and format values,
   but holds NO opinion about how the board looks. Rendering lives in each design. */
(function () {
  async function jget(url) { const r = await fetch(url); if (!r.ok) throw new Error(url + " -> " + r.status); return r.json(); }
  async function jsend(url, method) { const r = await fetch(url, { method }); return r.json(); }

  const LB = {
    // --- data ---
    board() { return jget("/api/board"); },
    panel(id) { return jget("/api/panel/" + id); },
    addTodo(text) {
      return fetch("/api/todos", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text })
      }).then(r => r.json());
    },
    toggleTodo(id) { return jsend("/api/todos/" + id + "/toggle", "POST"); },
    deleteTodo(id) { return jsend("/api/todos/" + id, "DELETE"); },
    tickHabit(pageId) { return jsend("/api/habits/" + pageId + "/tick", "POST"); },

    // --- shaping ---
    byId(board) {
      const m = {};
      (board.panels || []).forEach(p => { m[p.id] = p; });
      return m;
    },

    // --- formatting ---
    esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); },
    money(v, cur) {
      if (v == null) return "—";
      cur = cur || "£";
      return cur + Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
    signedPct(v) {
      if (v == null) return "—";
      const s = v >= 0 ? "+" : "";
      return s + Number(v).toFixed(2) + "%";
    },
    signedMoney(v, cur) {
      if (v == null) return "—";
      const s = v >= 0 ? "+" : "−";
      return s + (cur || "£") + Math.abs(Number(v)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    },
    clockFromISO(iso) {
      if (!iso) return "";
      const d = new Date(iso);
      if (isNaN(d)) return "";
      return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    },
    longDate(d) {
      d = d || new Date();
      return d.toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });
    },
    greeting(d) {
      const h = (d || new Date()).getHours();
      return h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
    },
    timeAgo(iso) {
      const d = new Date(iso);
      if (isNaN(d)) return "";
      const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
      if (s < 90) return "just now";
      const m = s / 60; if (m < 60) return Math.round(m) + "m ago";
      const h = m / 60; if (h < 24) return Math.round(h) + "h ago";
      const days = h / 24; return Math.round(days) + "d ago";
    }
  };
  window.LB = LB;
})();
