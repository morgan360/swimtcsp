/**
 * Shared chat widget for both bots. The two templates previously carried
 * ~95% identical copies of this, which drifted.
 *
 * The container element supplies its configuration:
 *   data-endpoint       URL to POST to
 *   data-rate-endpoint  URL for the thumbs up / down under each answer
 *   data-bot-name       label prefixed to each reply
 */
document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("chat-container");
  if (!container) return;

  const endpoint = container.dataset.endpoint;
  const rateEndpoint = container.dataset.rateEndpoint;
  const botName = container.dataset.botName || "Bot";

  const input = document.getElementById("chat-input");
  const log = document.getElementById("chat-log");
  const sendButton = document.getElementById("chat-send");
  const sendText = document.getElementById("send-text");
  const sendSpinner = document.getElementById("send-spinner");

  // The full-page chat wants focus straight away. The floating panel starts
  // hidden and focuses its own input when opened, so focusing here would put the
  // caret in an invisible field and can scroll the page on some browsers.
  if (input.offsetParent !== null) {
    input.focus();
  }

  function getCookie(name) {
    const match = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return match ? match.pop() : "";
  }

  function appendBubble(className) {
    const div = document.createElement("div");
    div.className = className;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function appendUserMessage(message) {
    const div = appendBubble("bg-blue-200 text-blue-900 rounded-lg p-4");
    const strong = document.createElement("strong");
    strong.textContent = "You: ";
    div.appendChild(strong);
    // textContent, not innerHTML: the message is raw user input.
    const span = document.createElement("span");
    span.textContent = message;
    div.appendChild(span);
  }

  function appendBotHTMLMessage(html) {
    const div = appendBubble("bg-blue-100 text-blue-800 rounded-lg p-4");
    // Server-side: FAQ answers are admin-authored, model output is sanitised.
    div.innerHTML = `<strong>${botName}:</strong> ${html}`;
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function typeBotMessage(message, delay = 15) {
    const div = appendBubble("bg-blue-100 text-blue-800 rounded-lg p-4");
    const strong = document.createElement("strong");
    strong.textContent = `${botName}: `;
    div.appendChild(strong);
    const span = document.createElement("span");
    div.appendChild(span);

    let i = 0;
    (function type() {
      if (i < message.length) {
        span.textContent += message.charAt(i);
        log.scrollTop = log.scrollHeight;
        i++;
        setTimeout(type, delay);
      }
    })();
    return div;
  }

  // Thumbs up or down under an answer. Only answers the server recorded come
  // with an id, so refusals and "too many messages" get no buttons.
  function addRating(bubble, id) {
    if (!rateEndpoint || !id) return;
    const bar = document.createElement("div");
    bar.className = "mt-2 flex items-center gap-2 text-sm";
    const label = document.createElement("span");
    label.className = "text-blue-700";
    label.textContent = "Was this helpful?";
    bar.appendChild(label);

    const buttons = [[1, "👍", "Helpful"], [-1, "👎", "Not helpful"]].map(([rating, icon, name]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "px-2 py-0.5 rounded border border-blue-300 hover:bg-blue-200";
      button.textContent = icon;
      button.title = name;
      button.setAttribute("aria-label", name);
      button.setAttribute("aria-pressed", "false");
      button.addEventListener("click", async () => {
        try {
          const response = await fetch(rateEndpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify({ id, rating }),
          });
          if (!response.ok) return;
          buttons.forEach((other) => {
            const chosen = other === button;
            other.setAttribute("aria-pressed", String(chosen));
            other.classList.toggle("bg-blue-300", chosen);
          });
          label.textContent = "Thanks for the feedback";
        } catch (err) {
          console.error(err);
        }
      });
      bar.appendChild(button);
      return button;
    });

    bubble.appendChild(bar);
    log.scrollTop = log.scrollHeight;
  }

  async function sendMessage() {
    const userMessage = input.value.trim();
    if (!userMessage) return;

    sendButton.disabled = true;
    sendText.textContent = "Thinking...";
    sendSpinner.classList.remove("hidden");

    appendUserMessage(userMessage);
    input.value = "";

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify({ message: userMessage }),
      });

      const data = await response.json();
      if (data.reply) {
        const bubble = /<[a-z][\s\S]*>/i.test(data.reply)
          ? appendBotHTMLMessage(data.reply)
          : typeBotMessage(data.reply);
        addRating(bubble, data.id);
      } else if (data.error) {
        typeBotMessage(data.error);
      } else {
        typeBotMessage("Sorry, I didn't catch that. Can you try rephrasing?");
      }
    } catch (err) {
      console.error(err);
      typeBotMessage("Oops! Something went wrong.");
    } finally {
      sendButton.disabled = false;
      sendText.textContent = "Send";
      sendSpinner.classList.add("hidden");
    }
  }

  sendButton.addEventListener("click", sendMessage);
  input.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      sendMessage();
    }
  });
});
