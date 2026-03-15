<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { AdminApiError, getEndpoint, previewResponse } from "../api/admin";
import { useAuth } from "../composables/useAuth";
import type { Endpoint } from "../types/endpoints";

const route = useRoute();
const router = useRouter();
const auth = useAuth();

const endpoint = ref<Endpoint | null>(null);
const pathParameters = ref<Record<string, string>>({});
const requestBody = ref("{}");
const samplePreview = ref<string | null>(null);
const previewResult = ref<{
  body: string;
  contentType: string;
  status: number;
  statusText: string;
} | null>(null);
const isLoading = ref(true);
const isRunning = ref(false);
const loadError = ref<string | null>(null);
const previewError = ref<string | null>(null);

const endpointId = computed(() => {
  const rawId = route.params.endpointId;
  return typeof rawId === "string" ? Number(rawId) : null;
});

watch(
  endpointId,
  () => {
    void loadEndpoint();
  },
  { immediate: true },
);

watch(endpoint, () => {
  if (endpoint.value) {
    void loadSamplePreview();
  }
});

function extractPathParameters(path: string): string[] {
  return Array.from(path.matchAll(/\{([^}]+)\}/g), (match) => match[1]);
}

function buildDefaultPathParameters(path: string): Record<string, string> {
  return extractPathParameters(path).reduce<Record<string, string>>((accumulator, key) => {
    accumulator[key] = `sample-${key}`;
    return accumulator;
  }, {});
}

function resolvePath(path: string, parameters: Record<string, string>): string {
  return path.replace(/\{([^}]+)\}/g, (_, key: string) => encodeURIComponent(parameters[key] || `sample-${key}`));
}

function prettyJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

async function loadEndpoint(): Promise<void> {
  if (!endpointId.value || !auth.session.value) {
    isLoading.value = false;
    loadError.value = "Missing endpoint id.";
    return;
  }

  isLoading.value = true;
  loadError.value = null;

  try {
    const loadedEndpoint = await getEndpoint(endpointId.value, auth.session.value);
    endpoint.value = loadedEndpoint;
    pathParameters.value = buildDefaultPathParameters(loadedEndpoint.path);
    requestBody.value = "{}";
  } catch (error) {
    if (error instanceof AdminApiError && error.status === 401) {
      void auth.logout("Your admin session expired. Sign in again before previewing endpoints.");
      void router.push({ name: "login" });
      return;
    }

    loadError.value = error instanceof Error ? error.message : "Unable to load the endpoint preview.";
  } finally {
    isLoading.value = false;
  }
}

async function loadSamplePreview(): Promise<void> {
  if (!endpoint.value || !auth.session.value) {
    return;
  }

  try {
    const response = await previewResponse(
      endpoint.value.response_schema ?? {},
      endpoint.value.seed_key ?? null,
      auth.session.value,
    );
    samplePreview.value = prettyJson(response.preview);
  } catch {
    samplePreview.value = null;
  }
}

async function runPreview(): Promise<void> {
  if (!endpoint.value) {
    return;
  }

  previewError.value = null;
  previewResult.value = null;
  isRunning.value = true;

  try {
    let body: string | undefined;

    if (!["GET", "DELETE"].includes(endpoint.value.method) && requestBody.value.trim()) {
      try {
        JSON.parse(requestBody.value);
        body = requestBody.value;
      } catch {
        previewError.value = "Request body must be valid JSON before running the preview.";
        isRunning.value = false;
        return;
      }
    }

    const response = await fetch(resolvePath(endpoint.value.path, pathParameters.value), {
      method: endpoint.value.method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body,
    });
    const responseText = await response.text();

    let renderedBody = responseText;
    try {
      renderedBody = prettyJson(JSON.parse(responseText));
    } catch {
      if (!responseText) {
        renderedBody = "(empty response)";
      }
    }

    previewResult.value = {
      status: response.status,
      statusText: response.statusText,
      contentType: response.headers.get("content-type") ?? "unknown",
      body: renderedBody,
    };
  } catch (error) {
    previewError.value = error instanceof Error ? error.message : "Unable to run the preview.";
  } finally {
    isRunning.value = false;
  }
}
</script>

<template>
  <div class="d-flex flex-column ga-4">
    <div class="d-flex flex-column flex-lg-row justify-space-between ga-4">
      <div>
        <div class="text-overline text-secondary">Public route preview</div>
        <div class="text-h3 font-weight-bold mt-2">{{ endpoint?.name || "Loading preview" }}</div>
        <div class="text-body-1 text-medium-emphasis mt-3">
          Run the public mock route directly so preview behavior matches live runtime dispatch.
        </div>
      </div>

      <div class="d-flex flex-wrap align-start justify-end ga-2">
        <v-btn
          prepend-icon="mdi-arrow-left"
          variant="text"
          @click="router.push({ name: endpoint ? 'endpoints-edit' : 'endpoints-browse', params: endpoint ? { endpointId: endpoint.id } : undefined })"
        >
          Back to settings
        </v-btn>
        <v-btn
          v-if="endpoint"
          prepend-icon="mdi-shape-outline"
          variant="text"
          @click="router.push({ name: 'schema-editor', params: { endpointId: endpoint.id } })"
        >
          Schema studio
        </v-btn>
      </div>
    </div>

    <v-skeleton-loader
      v-if="isLoading"
      class="workspace-card"
      type="heading, paragraph, paragraph, table-heading, table-row-divider, paragraph"
    />

    <v-card v-else-if="!endpoint" class="workspace-card">
      <v-card-text class="pa-8">
        <div class="text-overline text-error">Preview unavailable</div>
        <div class="text-h4 font-weight-bold mt-2">We could not load that endpoint.</div>
        <div class="text-body-1 text-medium-emphasis mt-4">
          {{ loadError ?? "The endpoint is missing or your session changed while loading the preview." }}
        </div>
      </v-card-text>
    </v-card>

    <template v-else>
      <v-card class="workspace-card">
        <v-card-text class="d-flex flex-wrap justify-space-between ga-3">
          <div class="d-flex flex-wrap ga-2">
            <v-chip color="primary" label variant="tonal">{{ endpoint.method }}</v-chip>
            <v-chip :color="endpoint.enabled ? 'accent' : 'surface-variant'" label variant="tonal">
              {{ endpoint.enabled ? "Live" : "Disabled" }}
            </v-chip>
            <v-chip label variant="outlined">{{ endpoint.path }}</v-chip>
          </div>
          <v-btn color="primary" :loading="isRunning" prepend-icon="mdi-play-circle-outline" @click="runPreview">
            Run preview
          </v-btn>
        </v-card-text>
      </v-card>

      <v-alert v-if="!endpoint.enabled" border="start" color="info" variant="tonal">
        This endpoint is disabled, so the public preview is expected to return a 404.
      </v-alert>

      <v-alert v-if="previewError" border="start" color="error" variant="tonal">
        {{ previewError }}
      </v-alert>

      <v-row dense>
        <v-col cols="12" lg="5">
          <v-card class="workspace-card fill-height">
            <v-card-item>
              <v-card-title>Request setup</v-card-title>
              <v-card-subtitle>Provide path parameters and a request body when the method expects one.</v-card-subtitle>
            </v-card-item>
            <v-divider />
            <v-card-text class="d-flex flex-column ga-4">
              <v-text-field
                v-for="key in extractPathParameters(endpoint.path)"
                :key="key"
                v-model="pathParameters[key]"
                :label="`Path param: ${key}`"
              />

              <v-textarea
                v-if="!['GET', 'DELETE'].includes(endpoint.method)"
                v-model="requestBody"
                auto-grow
                label="Request body JSON"
                rows="10"
              />

              <div v-if="samplePreview" class="d-flex flex-column ga-2">
                <div class="text-overline text-medium-emphasis">Schema sample</div>
                <pre class="code-block">{{ samplePreview }}</pre>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="7">
          <v-card class="workspace-card fill-height">
            <v-card-item>
              <v-card-title>Response</v-card-title>
              <v-card-subtitle>
                {{
                  previewResult
                    ? `${previewResult.status} ${previewResult.statusText} • ${previewResult.contentType}`
                    : "Run the public route to inspect the live response."
                }}
              </v-card-subtitle>
            </v-card-item>
            <v-divider />
            <v-card-text>
              <pre class="code-block">{{ previewResult?.body ?? "(run the preview to see the response body)" }}</pre>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </div>
</template>
