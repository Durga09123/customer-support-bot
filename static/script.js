(() => {
  const log = document.getElementById("log");
  const chips = document.getElementById("chips");
  const form = document.getElementById("form");
  const input = document.getElementById("input");
  const sendBtn = form.querySelector("button");

  function scrollDown() {
    log.scrollTop = log.scrollHeight;
  }

  function addUser(text) {
    const div = document.createElement("div");
    div.className = "msg msg--user";
    div.textContent = text;
    log.appendChild(div);
    scrollDown();
  }

  function buildTable(t) {
    const table = document.createElement("table");
    const thead = table.createTHead().insertRow();
    t.headers.forEach((h) => {
      const th = document.createElement("th");
      th.textContent = h;
      thead.appendChild(th);
    });
    const tbody = table.createTBody();
    t.rows.forEach((row) => {
      const tr = tbody.insertRow();
      row.forEach((cell) => (tr.insertCell().textContent = cell));
    });
    if (t.footer) {
      const tr = table.createTFoot().insertRow();
      t.footer.forEach((cell) => (tr.insertCell().textContent = cell));
    }
    return table;
  }

  function addBot(data) {
    const div = document.createElement("div");
    div.className = "msg msg--bot";
    div.appendChild(document.createTextNode(data.text));
    if (data.table) div.appendChild(buildTable(data.table));
    log.appendChild(div);
    setChips(data.suggestions || []);
    scrollDown();
  }

  function setChips(list) {
    chips.replaceChildren();
    list.forEach((label) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.addEventListener("click", () => send(label));
      chips.appendChild(b);
    });
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "msg msg--bot typing";
    div.innerHTML = "<span></span><span></span><span></span>";
    log.appendChild(div);
    scrollDown();
    return div;
  }

  async function send(text) {
    text = text.trim();
    if (!text) return;
    addUser(text);
    setChips([]);
    input.value = "";
    sendBtn.disabled = true;
    const typing = showTyping();
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      if (!res.ok) throw new Error("Request failed");
      const data = await res.json();
      typing.remove();
      addBot(data);
    } catch (err) {
      typing.remove();
      addBot({
        text: "Something went wrong. Please try again in a moment.",
        suggestions: ["View fruits"],
      });
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    send(input.value);
  });

  addBot({
    text:
      "Welcome to Fresh Fruit Shop!\n\nI can help you with fruit availability, prices and quantities.\n\nYou can ask:\n• Is apple available?\n• 2 kg apple\n• apple 1kg mango 2kg",
    suggestions: ["View fruits", "Is apple available?", "2 kg apple, 500 g mango"],
  });
})();
