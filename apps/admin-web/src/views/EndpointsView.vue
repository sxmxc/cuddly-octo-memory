<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  AdminApiError,
  createEndpoint,
  deleteEndpoint,
  listEndpoints,
  updateEndpoint,
} from "../api/admin";
import EndpointCatalog from "../components/EndpointCatalog.vue";
import EndpointSettingsForm from "../components/EndpointSettingsForm.vue";
import { useAuth } from "../composables/useAuth";
import type { Endpoint, EndpointDraft } from "../types/endpoints";
import {
  buildPayload,
  createDuplicateDraft,
  createEmptyDraft,
  describeAdminError,
  draftFromEndpoint,
} from "../utils/endpointDrafts";

const props = defineProps<{
  mode: "browse" | "create" | "edit";
}>();

const route = useRoute();
const router = useRouter();
const auth = useAuth();

const endpoints = ref<Endpoint[]>([]);
const draft = ref<EndpointDraft>(createEmptyDraft());
const fieldErrors = ref<Record<string, string>>({});
const isLoading = ref(false);
const isSaving = ref(false);
const catalogError = ref<string | null>(null);
const pageError = ref<string | null>(null);
const pageSuccess = ref<string | null>(null);

const endpointId = computed(() => {
  const rawId = route.params.endpointId;
  return typeof rawId === "string" ? Number(rawId) : null;
});

const duplicateSourceId = computed(() => {
  const rawId = Array.isArray(route.query.duplicateFrom) ? route.query.duplicateFrom[0] : route.query.duplicateFrom;
  if (typeof rawId !== "string") {
    return null;
  }

  const parsed = Number(rawId);
  return Number.isFinite(parsed) ? parsed : null;
});

const selectedEndpoint = computed(() =>
  endpointId.value ? endpoints.value.find((endpoint) => endpoint.id === endpointId.value) ?? null : null,
);

const duplicateSource = computed(() =>
  duplicateSourceId.value ? endpoints.value.find((endpoint) => endpoint.id === duplicateSourceId.value) ?? null : null,
);
const duplicateRequestNonce = computed(() => {
  const rawValue = Array.isArray(route.query.duplicateNonce) ? route.query.duplicateNonce[0] : route.query.duplicateNonce;
  return typeof rawValue === "string" ? rawValue : "";
});
const savedQueryFlag = computed(() => {
  const rawValue = Array.isArray(route.query.saved) ? route.query.saved[0] : route.query.saved;
  return rawValue === "1";
});

const isInitialCatalogLoad = computed(() => isLoading.value && endpoints.value.length === 0);
const recordTransitionKey = computed(() =>
  props.mode === "create" ? "create" : selectedEndpoint.value ? `endpoint-${selectedEndpoint.value.id}` : "empty",
);
const duplicateBanner = computed(() => {
  if (props.mode !== "create" || !duplicateSource.value) {
    return null;
  }

  return `Copied settings from ${duplicateSource.value.name}. Review the new name, slug, and path before saving.`;
});

async function fetchEndpoints(): Promise<void> {
  if (!auth.session.value) {
    endpoints.value = [];
    return;
  }

  isLoading.value = true;
  catalogError.value = null;

  try {
    endpoints.value = await listEndpoints(auth.session.value);
  } catch (error) {
    if (error instanceof AdminApiError && error.status === 401) {
      void auth.logout("Your admin session expired. Sign in again to keep editing.");
      void router.push({ name: "login" });
      return;
    }

    endpoints.value = [];
    catalogError.value = describeAdminError(error, "Unable to load endpoints.");
  } finally {
    isLoading.value = false;
  }
}

watch(
  () => auth.session.value,
  () => {
    void fetchEndpoints();
  },
  { immediate: true },
);

watch(
  [() => props.mode, selectedEndpoint, duplicateSource, duplicateRequestNonce, savedQueryFlag],
  () => {
    fieldErrors.value = {};
    pageError.value = null;
    pageSuccess.value = savedQueryFlag.value ? "Saved endpoint settings." : null;

    if (props.mode === "create") {
      draft.value = duplicateSource.value
        ? createDuplicateDraft(duplicateSource.value, endpoints.value)
        : createEmptyDraft();
      return;
    }

    if (props.mode === "edit" && selectedEndpoint.value) {
      draft.value = draftFromEndpoint(selectedEndpoint.value);
    }
  },
  { immediate: true },
);

function applyDraftPatch(patch: Partial<EndpointDraft>): void {
  draft.value = {
    ...draft.value,
    ...patch,
  };
}

function openCreateView(): void {
  void router.push({ name: "endpoints-create" });
}

function duplicateEndpoint(endpointId: number): void {
  void router.push({
    name: "endpoints-create",
    query: {
      duplicateFrom: String(endpointId),
      duplicateNonce: String(Date.now()),
    },
  });
}

async function handleSave(): Promise<void> {
  if (!auth.session.value) {
    pageError.value = "Sign in again before saving endpoints.";
    return;
  }

  pageError.value = null;
  pageSuccess.value = null;

  const { errors, payload } = buildPayload(draft.value);
  fieldErrors.value = errors;

  if (!payload || Object.keys(errors).length > 0) {
    return;
  }

  isSaving.value = true;

  try {
    if (props.mode === "create") {
      const createdEndpoint = await createEndpoint(payload, auth.session.value);
      endpoints.value = [createdEndpoint, ...endpoints.value];
      void router.push({ name: "endpoints-edit", params: { endpointId: createdEndpoint.id }, query: { saved: "1" } });
      return;
    }

    if (!selectedEndpoint.value) {
      pageError.value = "Select an endpoint before saving.";
      return;
    }

    const updatedEndpoint = await updateEndpoint(selectedEndpoint.value.id, payload, auth.session.value);
    endpoints.value = endpoints.value.map((endpoint) => (endpoint.id === updatedEndpoint.id ? updatedEndpoint : endpoint));
    pageSuccess.value = `Saved ${updatedEndpoint.name}.`;
  } catch (error) {
    if (error instanceof AdminApiError && error.status === 401) {
      void auth.logout("Your admin session expired. Sign in again before saving more changes.");
      void router.push({ name: "login" });
      return;
    }

    pageError.value = describeAdminError(error, "Unable to save the endpoint.");
  } finally {
    isSaving.value = false;
  }
}

async function handleDelete(): Promise<void> {
  if (!selectedEndpoint.value || !auth.session.value) {
    return;
  }

  const shouldDelete = window.confirm(`Delete "${selectedEndpoint.value.name}" from the catalog?`);
  if (!shouldDelete) {
    return;
  }

  isSaving.value = true;
  pageError.value = null;
  pageSuccess.value = null;

  try {
    await deleteEndpoint(selectedEndpoint.value.id, auth.session.value);
    endpoints.value = endpoints.value.filter((endpoint) => endpoint.id !== selectedEndpoint.value?.id);
    void router.push({ name: "endpoints-browse" });
  } catch (error) {
    if (error instanceof AdminApiError && error.status === 401) {
      void auth.logout("Your admin session expired. Sign in again before deleting endpoints.");
      void router.push({ name: "login" });
      return;
    }

    pageError.value = describeAdminError(error, "Unable to delete the endpoint.");
  } finally {
    isSaving.value = false;
  }
}

function openSchemaStudio(): void {
  if (!selectedEndpoint.value) {
    return;
  }

  void router.push({ name: "schema-editor", params: { endpointId: selectedEndpoint.value.id } });
}

function openPreview(): void {
  if (!selectedEndpoint.value) {
    return;
  }

  void router.push({ name: "endpoint-preview", params: { endpointId: selectedEndpoint.value.id } });
}

function duplicateSelectedEndpoint(): void {
  if (!selectedEndpoint.value) {
    return;
  }

  duplicateEndpoint(selectedEndpoint.value.id);
}

const activeTitle = computed(() => {
  if (props.mode === "create") {
    return "Start a new route";
  }

  if (!selectedEndpoint.value) {
    return "Choose a route";
  }

  return selectedEndpoint.value.name;
});
</script>

<template>
  <v-row class="workspace-grid endpoint-workspace-grid">
    <v-col class="endpoint-sidebar-col" cols="12" xl="3" lg="4">
      <div class="endpoint-sidebar">
        <EndpointCatalog
          :active-endpoint-id="selectedEndpoint?.id"
          :endpoints="endpoints"
          :error="catalogError"
          :loading="isLoading"
          @create="openCreateView"
          @duplicate="duplicateEndpoint"
          @refresh="fetchEndpoints"
          @select="(id) => router.push({ name: 'endpoints-edit', params: { endpointId: id } })"
        />
      </div>
    </v-col>

    <v-col class="endpoint-detail-col" cols="12" xl="9" lg="8">
      <div class="endpoint-detail-shell">
        <v-alert v-if="pageSuccess" border="start" color="success" variant="tonal">
          {{ pageSuccess }}
        </v-alert>

        <v-alert v-if="pageError" border="start" color="error" variant="tonal">
          {{ pageError }}
        </v-alert>

        <v-alert v-if="duplicateBanner" border="start" color="info" variant="tonal">
          {{ duplicateBanner }}
        </v-alert>

        <div class="endpoint-detail-scroll">
          <v-skeleton-loader
            v-if="isInitialCatalogLoad"
            class="workspace-card"
            type="heading, paragraph, paragraph, paragraph, table-heading, table-row-divider, table-row-divider"
          />

          <v-card v-else-if="props.mode === 'browse'" class="workspace-card browse-card">
            <v-card-text class="pa-8">
              <div class="text-overline text-secondary">Endpoint studio</div>
              <div class="text-h3 font-weight-bold mt-2">Pick a route from the catalog or start a new one.</div>
              <div class="text-body-1 text-medium-emphasis mt-4">
                Settings stay here. Schema design now gets its own full-page workspace so the builder is no longer
                competing with general form controls.
              </div>
              <div class="d-flex flex-wrap ga-3 mt-6">
                <v-btn color="primary" prepend-icon="mdi-plus" @click="router.push({ name: 'endpoints-create' })">
                  Create endpoint
                </v-btn>
                <v-btn prepend-icon="mdi-refresh" variant="text" @click="fetchEndpoints">
                  Refresh catalog
                </v-btn>
              </div>
            </v-card-text>
          </v-card>

          <v-card
            v-else-if="props.mode === 'edit' && !selectedEndpoint"
            class="workspace-card browse-card"
          >
            <v-card-text class="pa-8">
              <div class="text-overline text-error">Missing endpoint</div>
              <div class="text-h4 font-weight-bold mt-2">That route is no longer in the catalog.</div>
              <div class="text-body-1 text-medium-emphasis mt-4">
                Refresh the list, pick another record, or create a fresh endpoint shell.
              </div>
            </v-card-text>
          </v-card>

          <template v-else>
            <v-slide-y-transition mode="out-in">
              <div :key="recordTransitionKey" class="d-flex flex-column ga-4">
                <v-card class="workspace-card record-hero">
                  <v-card-text class="d-flex flex-column flex-md-row justify-space-between ga-4">
                    <div>
                      <div class="text-overline text-secondary">
                        {{ props.mode === "create" ? "New route shell" : "Active record" }}
                      </div>
                      <div class="text-h4 font-weight-bold mt-2">{{ activeTitle }}</div>
                      <div class="text-body-1 text-medium-emphasis mt-3">
                        {{
                          props.mode === "create"
                            ? "Start with identity and behavior. Once the endpoint exists, the schema studio opens on its own page."
                            : selectedEndpoint?.path
                        }}
                      </div>
                    </div>

                    <div class="d-flex flex-wrap align-start justify-end ga-2">
                      <v-chip v-if="selectedEndpoint" color="primary" label variant="tonal">
                        {{ selectedEndpoint.method }}
                      </v-chip>
                      <v-chip v-if="selectedEndpoint" :color="selectedEndpoint.enabled ? 'accent' : 'surface-variant'" label variant="tonal">
                        {{ selectedEndpoint.enabled ? "Live" : "Disabled" }}
                      </v-chip>
                      <v-chip v-if="selectedEndpoint?.category" color="secondary" label variant="tonal">
                        {{ selectedEndpoint.category }}
                      </v-chip>
                    </div>
                  </v-card-text>
                </v-card>

                <EndpointSettingsForm
                  :created-at="selectedEndpoint?.created_at"
                  :draft="draft"
                  :endpoint-id="selectedEndpoint?.id"
                  :errors="fieldErrors"
                  :is-creating="props.mode === 'create'"
                  :is-saving="isSaving"
                  :updated-at="selectedEndpoint?.updated_at"
                  @change="applyDraftPatch"
                  @delete="handleDelete"
                  @duplicate="duplicateSelectedEndpoint"
                  @open-schema="openSchemaStudio"
                  @preview="openPreview"
                  @submit="handleSave"
                />
              </div>
            </v-slide-y-transition>
          </template>
        </div>
      </div>
    </v-col>
  </v-row>
</template>

<style scoped>
.endpoint-sidebar,
.endpoint-detail-shell {
  width: 100%;
}

.endpoint-detail-shell {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.endpoint-detail-scroll {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
}

@media (min-width: 1280px) {
  .endpoint-workspace-grid {
    min-height: calc(100vh - var(--v-layout-top, 88px) - 3rem);
  }

  .endpoint-detail-col {
    display: flex;
  }

  .endpoint-sidebar-col {
    display: flex;
    position: sticky;
    top: 0;
    align-self: flex-start;
  }

  .endpoint-sidebar {
    height: calc(100vh - var(--v-layout-top, 88px) - 3rem);
    max-height: calc(100vh - var(--v-layout-top, 88px) - 3rem);
  }
}
</style>
