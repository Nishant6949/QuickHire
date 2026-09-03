(function () {
  const trigger = document.getElementById('notification-trigger');
  const panel = document.getElementById('notification-panel');
  const list = document.getElementById('notification-list');
  const badge = document.getElementById('notification-badge');
  const readAll = document.getElementById('notification-read-all');
  if (!trigger || !panel || !list || !badge) return;

  const escapeHtml = (value) => String(value || '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const timeAgo = (iso) => {
    if (!iso) return '';
    const seconds = Math.max(1, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds/60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds/3600)}h ago`;
    return `${Math.floor(seconds/86400)}d ago`;
  };

  async function loadNotifications() {
    try {
      const response = await fetch('/dashboard/notifications', {headers: {'Accept':'application/json'}});
      const data = await response.json();
      if (!data.success) throw new Error('Unable to load');
      badge.textContent = data.unread > 99 ? '99+' : data.unread;
      badge.hidden = !data.unread;
      if (!data.notifications.length) {
        list.innerHTML = '<div class="notification-empty"><strong>You’re all caught up</strong><span>New applications and hiring updates will appear here.</span></div>';
        return;
      }
      list.innerHTML = data.notifications.map(n => `
        <a class="notification-item ${n.is_read ? '' : 'unread'}" href="${escapeHtml(n.link || '#')}" data-id="${n.id}">
          <span class="notification-dot"></span><span class="notification-copy"><strong>${escapeHtml(n.title)}</strong><span>${escapeHtml(n.message)}</span><small>${timeAgo(n.created_at)}</small></span>
        </a>`).join('');
      list.querySelectorAll('.notification-item').forEach(item => item.addEventListener('click', () => {
        fetch(`/dashboard/notifications/${item.dataset.id}/read`, {method:'PATCH', headers:{'Content-Type':'application/json'}}).catch(()=>{});
      }));
    } catch (e) {
      list.innerHTML = '<div class="notification-empty">Notifications are temporarily unavailable.</div>';
    }
  }

  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    const open = panel.classList.toggle('is-open');
    panel.setAttribute('aria-hidden', !open);
    trigger.setAttribute('aria-expanded', open);
    if (open) loadNotifications();
  });
  panel.addEventListener('click', e => e.stopPropagation());
  document.addEventListener('click', () => { panel.classList.remove('is-open'); panel.setAttribute('aria-hidden','true'); trigger.setAttribute('aria-expanded','false'); });
  if (readAll) readAll.addEventListener('click', async () => {
    await fetch('/dashboard/notifications/read-all', {method:'POST', headers:{'Content-Type':'application/json'}});
    loadNotifications();
  });
  loadNotifications();
})();
