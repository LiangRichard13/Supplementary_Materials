<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
/* 全局样式和颜色变量 */
:root {
  --bg: #f8fafc;
  --card: #ffffff;
  --text: #1e293b;
  --muted: #64748b;
  --accent: #3b82f6;
  --accent-2: #10b981;
  --border: #e2e8f0;
  --shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  background: var(--bg);
  font-family: "Inter", system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
  color: var(--text);
}

#app {
  height: 100%;
  background: var(--bg);
}
</style>
