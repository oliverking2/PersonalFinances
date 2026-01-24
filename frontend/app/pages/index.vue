<!-- ==========================================================================
Index Page
Redirects to dashboard - the app's main entry point after auth
============================================================================ -->

<script setup lang="ts">
// Redirect to dashboard on load
// Auth middleware will handle redirecting to login if not authenticated
definePageMeta({
  middleware: () => navigateTo('/dashboard'),
})
</script>

<template>
  <!-- This template is never shown - immediate redirect to /dashboard -->
  <div />
</template>
