<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";
import { useTheme } from "vuetify";
import { ensureAuthBooted, useAuth } from "./composables/useAuth";
import { useStudioTheme } from "./composables/useStudioTheme";
import { getPageTransitionKey } from "./utils/routeTransitions";

const route = useRoute();
const router = useRouter();
const auth = useAuth();
const vuetifyTheme = useTheme();
const studioTheme = useStudioTheme();

onMounted(async () => {
  vuetifyTheme.global.name.value = studioTheme.mode.value;
  await ensureAuthBooted();
});

watch(
  studioTheme.mode,
  (value) => {
    vuetifyTheme.global.name.value = value;
  },
  { immediate: true },
);

const pageTitle = computed(() => (typeof route.meta.title === "string" ? route.meta.title : "Mockingbird Studio"));
const pageTransitionKey = computed(() => getPageTransitionKey(route));
const isPublicRoute = computed(() => route.name === "login");

function toggleTheme(): void {
  studioTheme.toggle();
}

function goToCatalog(): void {
  void router.push({ name: "endpoints-browse" });
}

function goToSecurity(): void {
  void router.push({ name: "security" });
}

async function signOut(): Promise<void> {
  await auth.logout("You signed out of the admin studio.");
  void router.push({ name: "login" });
}
</script>

<template>
  <v-app class="studio-app">
    <v-app-bar class="studio-topbar" flat height="88">
      <v-container class="d-flex align-center justify-space-between fill-height px-4" fluid>
        <div class="d-flex align-center ga-4">
          <div class="brand-mark">
            <img alt="Mockingbird logo" class="brand-mark-image" src="/mockingbird-icon.svg">
          </div>
          <div>
            <div class="text-overline text-medium-emphasis">Mockingbird</div>
            <div class="text-h5 font-weight-bold">{{ pageTitle }}</div>
          </div>
        </div>

        <div class="d-flex align-center ga-3">
          <v-chip
            v-if="auth.status.value === 'restoring'"
            color="info"
            label
            prepend-icon="mdi-cloud-sync-outline"
            variant="tonal"
          >
            Reconnecting
          </v-chip>

          <template v-else-if="auth.isAuthenticated.value">
            <v-btn
              :active="route.name === 'endpoints-browse' || route.name === 'endpoints-edit' || route.name === 'endpoints-create'"
              prepend-icon="mdi-view-dashboard-outline"
              variant="text"
              @click="goToCatalog"
            >
              Catalog
            </v-btn>
            <v-btn
              :active="route.name === 'security'"
              prepend-icon="mdi-shield-account-outline"
              variant="text"
              @click="goToSecurity"
            >
              Security
            </v-btn>
            <v-chip color="secondary" label prepend-icon="mdi-account-circle-outline" variant="tonal">
              {{ auth.username.value }}
            </v-chip>
            <v-chip
              v-if="auth.mustChangePassword.value"
              color="warning"
              label
              prepend-icon="mdi-lock-reset"
              variant="tonal"
            >
              Password reset required
            </v-chip>
          </template>

          <v-btn
            :icon="studioTheme.isDark.value ? 'mdi-weather-sunny' : 'mdi-weather-night'"
            variant="text"
            @click="toggleTheme"
          />

          <v-btn
            v-if="auth.isAuthenticated.value && !isPublicRoute"
            prepend-icon="mdi-logout"
            variant="text"
            @click="void signOut()"
          >
            Sign out
          </v-btn>
        </div>
      </v-container>
    </v-app-bar>

    <v-main class="studio-main">
      <v-container class="studio-shell fill-height px-3 px-sm-6 py-6" fluid>
        <router-view v-slot="{ Component }">
          <v-fade-transition mode="out-in">
            <component :is="Component" :key="pageTransitionKey" />
          </v-fade-transition>
        </router-view>
      </v-container>
    </v-main>
  </v-app>
</template>
