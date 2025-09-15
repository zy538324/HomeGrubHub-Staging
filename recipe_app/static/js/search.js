(function() {
  const input = document.getElementById('search-input');
  const list = document.getElementById('search-results');
  if (!input || !list) return;

  let timeout;

  input.addEventListener('input', () => {
    clearTimeout(timeout);
    const query = input.value.trim();
    if (!query) {
      list.innerHTML = '';
      return;
    }

    timeout = setTimeout(async () => {
      try {
        const res = await fetch(`/api/search?s=${encodeURIComponent(query)}`);
        if (!res.ok) return;
        const data = await res.json();
        list.innerHTML = '';
        data.forEach(title => {
          const option = document.createElement('option');
          option.value = title;
          list.appendChild(option);
        });
      } catch (err) {
        console.error('Search suggestions failed', err);
      }
    }, 300);
  });
})();
