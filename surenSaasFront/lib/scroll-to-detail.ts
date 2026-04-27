export function scrollToDetail() {
  setTimeout(() => {
    const el = document.getElementById('detail-card');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 50);
}
