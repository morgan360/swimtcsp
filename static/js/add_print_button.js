document.addEventListener("DOMContentLoaded", function() {
  const objectTools = document.querySelector(".object-tools");
  if (objectTools) {
    const printUrl = window.location.pathname + "print/?" + window.location.search;
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = printUrl;
    a.textContent = "🖨 Print";
    a.classList.add("button");
    li.appendChild(a);
    objectTools.prepend(li);
  }
});