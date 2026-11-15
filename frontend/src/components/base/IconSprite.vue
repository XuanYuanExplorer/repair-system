<script setup lang="ts">
/**
 * 内联 SVG 图标雪碧图（设计稿 24 个 symbol + 少量补齐件）。
 * 统一 stroke:currentColor / stroke-width:1.7 / fill:none，禁止图标字体。
 */
</script>

<template>
  <svg xmlns="http://www.w3.org/2000/svg" style="display: none" aria-hidden="true">
    <defs>
      <!-- 设计稿原生图标 -->
      <symbol id="i-bell" viewBox="0 0 24 24"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" /></symbol>
      <symbol id="i-tool" viewBox="0 0 24 24"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" /></symbol>
      <symbol id="i-doc" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" /></symbol>
      <symbol id="i-card" viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" /><path d="M1 10h22" /></symbol>
      <symbol id="i-bed" viewBox="0 0 24 24"><path d="M2 4v16M2 8h18a2 2 0 0 1 2 2v10M2 17h20M6 8v9" /></symbol>
      <symbol id="i-cal" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></symbol>
      <symbol id="i-grid" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /></symbol>
      <symbol id="i-user" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></symbol>
      <symbol id="i-phone" viewBox="0 0 24 24"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z" /></symbol>
      <symbol id="i-msg" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></symbol>
      <symbol id="i-star" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 21 12 17.77 5.82 21 7 14.14 2 9.27l6.91-1.01z" /></symbol>
      <symbol id="i-check" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M8 12.5l2.6 2.6L16 9.5" /></symbol>
      <symbol id="i-chev" viewBox="0 0 24 24"><path d="M9 18l6-6-6-6" /></symbol>
      <symbol id="i-search" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" /></symbol>
      <symbol id="i-cam" viewBox="0 0 24 24"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" /><circle cx="12" cy="13" r="4" /></symbol>
      <symbol id="i-drop" viewBox="0 0 24 24"><path d="M12 2.69l5.66 5.66a8 8 0 1 1-11.31 0z" /></symbol>
      <symbol id="i-zap" viewBox="0 0 24 24"><path d="M13 2L3 14h9l-1 8 10-12h-9z" /></symbol>
      <symbol id="i-shield" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></symbol>
      <symbol id="i-clock" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></symbol>
      <symbol id="i-alert" viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><path d="M12 9v4M12 17h.01" /></symbol>
      <symbol id="i-lock" viewBox="0 0 24 24"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></symbol>
      <symbol id="i-clip" viewBox="0 0 24 24"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /></symbol>
      <symbol id="i-broom" viewBox="0 0 24 24"><path d="M19 3l-7.5 7.5M4 21c1-4 4-7 8-8l3 3c-1 4-4 7-8 8zM4 21h7" /></symbol>
      <symbol id="i-wifi2" viewBox="0 0 24 24"><path d="M5 12.55a11 11 0 0 1 14.08 0M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01M1.42 9a16 16 0 0 1 21.16 0" /></symbol>

      <!-- 补齐件（同一套线条规范） -->
      <symbol id="i-close" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12" /></symbol>
      <symbol id="i-plus" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" /></symbol>
      <symbol id="i-minus" viewBox="0 0 24 24"><path d="M5 12h14" /></symbol>
      <symbol id="i-copy" viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="1" /><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1" /></symbol>
      <symbol id="i-edit" viewBox="0 0 24 24"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z" /></symbol>
      <symbol id="i-logout" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="M16 17l5-5-5-5M21 12H9" /></symbol>
      <symbol id="i-mail" viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="M2 7l10 6 10-6" /></symbol>
      <symbol id="i-key" viewBox="0 0 24 24"><circle cx="7.5" cy="15.5" r="4.5" /><path d="M11 12L21 2M17 6l3 3M14 9l2 2" /></symbol>
      <symbol id="i-refresh" viewBox="0 0 24 24"><path d="M21 12a9 9 0 1 1-3-6.7M21 3v6h-6" /></symbol>
      <symbol id="i-arrow" viewBox="0 0 24 24"><path d="M5 12h14M13 6l6 6-6 6" /></symbol>
      <symbol id="i-download" viewBox="0 0 24 24"><path d="M12 3v12M7 11l5 5 5-5M4 21h16" /></symbol>
    </defs>
  </svg>
</template>
