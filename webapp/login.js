async function onTelegramAuth(user) {
  try {
    const res = await fetch("/api/auth/telegram-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(user),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    location.href = "index.html";
  } catch (e) {
    console.error(e);
    document.getElementById("loginError")?.classList.remove("d-none");
  }
}