<script setup lang="ts">
import { computed, ref, shallowRef, watch } from "vue";
import { useRouter } from "vue-router";
import { AdminApiError, previewResponse } from "../api/admin";
import SchemaNodeCard from "./SchemaNodeCard.vue";
import { useAuth } from "../composables/useAuth";
import {
  formatForValueType,
  GENERATOR_OPTIONS,
  PALETTE_TYPES,
  addNodeToContainer,
  canAcceptChildren,
  deleteNode,
  duplicateNode,
  findNode,
  insertNewNodeAfterSibling,
  moveNodeAfterSibling,
  moveNodeToContainer,
  recommendedMaxLengthForValueType,
  resetNodeType,
  schemaToTree,
  treeToSchema,
  updateNode,
  type BuilderNodeType,
  type BuilderScope,
  type MockMode,
  type SchemaBuilderNode,
} from "../schemaBuilder";
import type { JsonObject, JsonValue } from "../types/endpoints";

type DragPayload = { kind: "palette"; nodeType: BuilderNodeType } | { kind: "node"; nodeId: string };

const props = defineProps<{
  schema: JsonObject;
  scope: BuilderScope;
  seedKey?: string;
}>();

const emit = defineEmits<{
  "update:schema": [schema: JsonObject];
}>();

const auth = useAuth();
const router = useRouter();

const rootShapeOptions = [
  { title: "Object", value: "object" },
  { title: "Array", value: "array" },
  { title: "String", value: "string" },
  { title: "Enum", value: "enum" },
  { title: "Integer", value: "integer" },
  { title: "Number", value: "number" },
  { title: "Boolean", value: "boolean" },
] as const;

const stringFormatOptions = [
  { title: "Plain text", value: "" },
  { title: "Email", value: "email" },
  { title: "UUID", value: "uuid" },
  { title: "URL", value: "uri" },
  { title: "Date", value: "date" },
  { title: "DateTime", value: "date-time" },
  { title: "Time", value: "time" },
];

const modeOptions = [
  { title: "True random", value: "generate" },
  { title: "Mocking random", value: "mocking" },
  { title: "Static", value: "fixed" },
];

const tree = shallowRef<SchemaBuilderNode>(schemaToTree(props.schema, props.scope));
const selectedNodeId = ref(tree.value.id);
const importDialog = ref(false);
const importError = ref<string | null>(null);
const importText = ref("");
const dragPayload = ref<DragPayload | null>(null);
const previewStatus = ref<"idle" | "loading" | "success" | "error">("idle");
const previewBody = ref("");
const previewError = ref<string | null>(null);
const fixedJsonDraft = ref("");
const fixedJsonError = ref<string | null>(null);
let previewTimer: number | null = null;

const serializedIncomingSchema = computed(() => JSON.stringify(props.schema ?? {}));
const normalizedSeedKey = computed(() => {
  const trimmed = props.seedKey?.trim() ?? "";
  return trimmed ? trimmed : null;
});

const liveSchema = ref<JsonObject>({});
const selectedNode = shallowRef<SchemaBuilderNode>(tree.value);
const selectedParent = shallowRef<SchemaBuilderNode | null>(null);
const selectedIsRoot = computed(() => selectedNode.value.id === tree.value.id);
const selectedCanAcceptChildren = computed(() => canAcceptChildren(selectedNode.value));
const showValueTypeSelector = computed(() => {
  if (props.scope !== "response" || selectedNode.value.mode === "fixed") {
    return false;
  }

  return availableGenerators.value.length > 1;
});
const availableGenerators = computed(() => {
  const type = selectedNode.value.type;
  return GENERATOR_OPTIONS.filter((option) => option.types.includes(type));
});

function toSchemaSnapshot(nextTree: SchemaBuilderNode): JsonObject {
  return treeToSchema(nextTree, props.scope) as JsonObject;
}

liveSchema.value = toSchemaSnapshot(tree.value);

watch(
  serializedIncomingSchema,
  (serialized) => {
    const current = JSON.stringify(liveSchema.value);
    if (serialized === current) {
      return;
    }

    tree.value = schemaToTree(props.schema, props.scope);
    liveSchema.value = toSchemaSnapshot(tree.value);
    selectedNodeId.value = tree.value.id;
  },
  { immediate: true },
);

watch(
  [tree, selectedNodeId],
  () => {
    selectedNode.value = findNode(tree.value, selectedNodeId.value) ?? tree.value;
    selectedParent.value = findParentNode(tree.value, selectedNodeId.value);
  },
  { immediate: true },
);

watch(
  () => [selectedNode.value.id, selectedNode.value.mode, selectedNode.value.fixedValue],
  () => {
    if (selectedNode.value.type === "object" || selectedNode.value.type === "array") {
      fixedJsonDraft.value = JSON.stringify(selectedNode.value.fixedValue, null, 2);
    } else {
      fixedJsonDraft.value = "";
    }

    fixedJsonError.value = null;
  },
  { immediate: true, deep: true },
);

watch(
  () => JSON.stringify(liveSchema.value),
  () => {
    if (props.scope !== "response") {
      return;
    }

    if (previewTimer) {
      window.clearTimeout(previewTimer);
    }

    previewTimer = window.setTimeout(() => {
      void runPreview();
    }, 350);
  },
  { immediate: true },
);

watch(normalizedSeedKey, () => {
  if (props.scope === "response") {
    void runPreview();
  }
});

function findParentNode(root: SchemaBuilderNode, targetId: string, parent: SchemaBuilderNode | null = null): SchemaBuilderNode | null {
  if (root.id === targetId) {
    return parent;
  }

  for (const child of root.children) {
    const result = findParentNode(child, targetId, root);
    if (result) {
      return result;
    }
  }

  if (root.item) {
    const result = findParentNode(root.item, targetId, root);
    if (result) {
      return result;
    }
  }

  return null;
}

function commitTree(nextTree: SchemaBuilderNode): void {
  tree.value = nextTree;
  liveSchema.value = toSchemaSnapshot(nextTree);

  if (!findNode(nextTree, selectedNodeId.value)) {
    selectedNodeId.value = nextTree.id;
  }

  emit("update:schema", liveSchema.value);
}

function startPaletteDrag(nodeType: BuilderNodeType): void {
  dragPayload.value = { kind: "palette", nodeType };
}

function startNodeDrag(nodeId: string): void {
  dragPayload.value = { kind: "node", nodeId };
}

function clearDragPayload(): void {
  dragPayload.value = null;
}

function addFromPalette(nodeType: BuilderNodeType): void {
  const currentNode = selectedNode.value;
  const parentNode = selectedParent.value;

  if (canAcceptChildren(currentNode)) {
    commitTree(addNodeToContainer(tree.value, currentNode.id, nodeType, props.scope));
    return;
  }

  if (parentNode?.type === "object") {
    commitTree(insertNewNodeAfterSibling(tree.value, currentNode.id, nodeType, props.scope));
    return;
  }

  commitTree(addNodeToContainer(tree.value, tree.value.id, nodeType, props.scope));
}

function handleDropOnContainer(containerId: string): void {
  if (!dragPayload.value) {
    return;
  }

  if (dragPayload.value.kind === "palette") {
    commitTree(addNodeToContainer(tree.value, containerId, dragPayload.value.nodeType, props.scope));
  } else {
    commitTree(moveNodeToContainer(tree.value, dragPayload.value.nodeId, containerId));
  }

  clearDragPayload();
}

function handleDropAfterRow(nodeId: string): void {
  if (!dragPayload.value) {
    return;
  }

  if (dragPayload.value.kind === "palette") {
    commitTree(insertNewNodeAfterSibling(tree.value, nodeId, dragPayload.value.nodeType, props.scope));
  } else {
    commitTree(moveNodeAfterSibling(tree.value, dragPayload.value.nodeId, nodeId));
  }

  clearDragPayload();
}

function updateSelectedNode(
  updater: (node: SchemaBuilderNode, parent: SchemaBuilderNode | null) => SchemaBuilderNode,
): void {
  commitTree(updateNode(tree.value, selectedNode.value.id, updater));
}

function updateStructuredFixedValue(rawValue: string): void {
  fixedJsonDraft.value = rawValue;

  try {
    const parsed = JSON.parse(rawValue) as JsonValue;
    updateSelectedNode((node) => ({
      ...node,
      fixedValue: parsed,
    }));
    fixedJsonError.value = null;
  } catch {
    fixedJsonError.value = "Use valid JSON for fixed object and array values.";
  }
}

function updateEnumValues(rawValue: string): void {
  const enumValues = rawValue
    .split(/\r?\n|,/)
    .map((value) => value.trim())
    .filter(Boolean);

  updateSelectedNode((node) => ({
    ...node,
    enumValues,
  }));
}

function updateSelectedValueType(rawValue: unknown): void {
  const valueType = String(rawValue ?? "").trim() || null;
  const nextFormat = selectedNode.value.type === "string" ? formatForValueType(valueType) : selectedNode.value.format;
  const currentRecommendedLength = recommendedMaxLengthForValueType(selectedNode.value.generator);
  const nextRecommendedLength = recommendedMaxLengthForValueType(valueType);

  updateSelectedNode((node) => ({
    ...node,
    generator: valueType,
    format: node.type === "string" ? nextFormat : node.format,
    maxLength:
      node.type !== "string"
        ? node.maxLength
        : node.maxLength == null
          ? nextRecommendedLength
          : node.maxLength === currentRecommendedLength
            ? nextRecommendedLength
            : valueType === "long_text" && node.maxLength < nextRecommendedLength
              ? nextRecommendedLength
              : node.maxLength,
  }));
}

async function copySchema(): Promise<void> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(JSON.stringify(liveSchema.value, null, 2));
  }
}

function importSchema(): void {
  importError.value = null;

  try {
    const parsed = JSON.parse(importText.value) as JsonValue;
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      importError.value = "Import a JSON Schema object.";
      return;
    }

    tree.value = schemaToTree(parsed as JsonObject, props.scope);
    liveSchema.value = toSchemaSnapshot(tree.value);
    selectedNodeId.value = tree.value.id;
    emit("update:schema", liveSchema.value);
    importDialog.value = false;
  } catch {
    importError.value = "That JSON could not be parsed.";
  }
}

function removeSelectedNode(): void {
  if (selectedIsRoot.value) {
    return;
  }

  const fallbackSelection = selectedParent.value?.id ?? tree.value.id;
  commitTree(deleteNode(tree.value, selectedNode.value.id));
  selectedNodeId.value = fallbackSelection;
}

function duplicateSelectedNode(): void {
  if (selectedIsRoot.value) {
    return;
  }

  commitTree(duplicateNode(tree.value, selectedNode.value.id));
}

async function runPreview(force = false): Promise<void> {
  if (props.scope !== "response" || !auth.session.value) {
    return;
  }

  if (!force && previewStatus.value === "loading") {
    return;
  }

  previewStatus.value = "loading";
  previewError.value = null;

  try {
    const response = await previewResponse(liveSchema.value, normalizedSeedKey.value, auth.session.value);
    previewBody.value = JSON.stringify(response.preview, null, 2);
    previewStatus.value = "success";
  } catch (error) {
    if (error instanceof AdminApiError && error.status === 401) {
      void auth.logout("Your admin session expired. Sign in again before previewing response schemas.");
      void router.push({ name: "login" });
      return;
    }

    previewStatus.value = "error";
    previewError.value = error instanceof Error ? error.message : "Unable to generate a schema preview.";
  }
}

function previewModeLabel(mode: MockMode): string {
  if (mode === "fixed") {
    return "static";
  }

  if (mode === "mocking") {
    return "mocking";
  }

  return "random";
}
</script>

<template>
  <v-row class="schema-studio-grid" @dragend="clearDragPayload">
    <v-col class="schema-sidebar-col" cols="12" xl="3" lg="3">
      <div class="schema-sidebar d-flex flex-column ga-4">
        <v-card class="workspace-card">
          <v-card-item>
            <template #prepend>
              <v-avatar color="secondary" variant="tonal">
                <v-icon icon="mdi-pill" />
              </v-avatar>
            </template>

            <v-card-title>Palette</v-card-title>
            <v-card-subtitle>Use draggable Vuetify chips or click to add around the selected node.</v-card-subtitle>
          </v-card-item>
          <v-divider />
          <v-card-text class="d-flex flex-column ga-4">
            <div class="d-flex flex-wrap ga-3">
              <v-chip
                v-for="item in PALETTE_TYPES"
                :key="item.type"
                class="schema-pill"
                color="primary"
                :draggable="true"
                label
                variant="outlined"
                @click="addFromPalette(item.type)"
                @dragstart="startPaletteDrag(item.type)"
              >
                {{ item.label }}
              </v-chip>
            </div>

            <v-alert border="start" color="info" icon="mdi-cursor-move" variant="tonal">
              Drag chips into object or array containers, or click a chip to insert it near the selected node.
            </v-alert>
          </v-card-text>
        </v-card>

        <v-card class="workspace-card">
          <v-card-item>
            <v-card-title>Root shape</v-card-title>
            <v-card-subtitle>Switch the top-level contract without leaving the studio.</v-card-subtitle>
          </v-card-item>
          <v-divider />
          <v-card-text>
            <v-btn-toggle
              class="root-shape-toggle"
              divided
              mandatory
              :model-value="tree.type"
              @update:model-value="(value) => value && commitTree(resetNodeType(tree, tree.id, value, scope))"
            >
              <v-btn v-for="option in rootShapeOptions" :key="option.value" :value="option.value" size="small">
                {{ option.title }}
              </v-btn>
            </v-btn-toggle>
          </v-card-text>
        </v-card>

        <v-card class="workspace-card">
          <v-card-item>
            <template #prepend>
              <v-avatar color="accent" variant="tonal">
                <v-icon icon="mdi-tune-variant" />
              </v-avatar>
            </template>

            <v-card-title>Inspector</v-card-title>
            <v-card-subtitle>Edit the selected node instead of juggling raw JSON.</v-card-subtitle>

            <template #append>
              <div class="d-flex ga-2">
                <v-btn
                  :disabled="selectedIsRoot"
                  icon="mdi-content-copy"
                  size="small"
                  variant="text"
                  @click="duplicateSelectedNode"
                />
                <v-btn
                  :disabled="selectedIsRoot"
                  color="error"
                  icon="mdi-delete-outline"
                  size="small"
                  variant="text"
                  @click="removeSelectedNode"
                />
              </div>
            </template>
          </v-card-item>

          <v-divider />

          <v-card-text class="d-flex flex-column ga-4">
            <v-text-field
              :disabled="selectedIsRoot"
              label="Field name"
              :model-value="selectedNode.name"
              @update:model-value="updateSelectedNode((node) => ({ ...node, name: String($event ?? '') }))"
            />

            <v-select
              :items="rootShapeOptions"
              item-title="title"
              item-value="value"
              label="Node type"
              :model-value="selectedNode.type"
              @update:model-value="(value) => value && commitTree(resetNodeType(tree, selectedNode.id, value, scope))"
            />

            <v-textarea
              auto-grow
              label="Description"
              :model-value="selectedNode.description"
              rows="2"
              @update:model-value="updateSelectedNode((node) => ({ ...node, description: String($event ?? '') }))"
            />

            <v-switch
              v-if="!selectedIsRoot && selectedParent?.type === 'object'"
              color="accent"
              inset
              label="Required field"
              :model-value="selectedNode.required"
              @update:model-value="updateSelectedNode((node) => ({ ...node, required: Boolean($event) }))"
            />

            <v-select
              v-if="scope === 'response'"
              :items="modeOptions"
              item-title="title"
              item-value="value"
              label="Value mode"
              :model-value="selectedNode.mode"
              @update:model-value="updateSelectedNode((node) => ({ ...node, mode: String($event ?? 'generate') as MockMode }))"
            />

            <v-select
              v-if="showValueTypeSelector"
              :items="availableGenerators"
              item-title="label"
              item-value="value"
              label="Value type"
              :model-value="selectedNode.generator"
              @update:model-value="updateSelectedValueType"
            />

            <v-select
              v-if="selectedNode.type === 'string'"
              :items="stringFormatOptions"
              item-title="title"
              item-value="value"
              label="Format"
              :model-value="selectedNode.format"
              @update:model-value="updateSelectedNode((node) => ({ ...node, format: String($event ?? '') }))"
            />

            <v-row v-if="selectedNode.type === 'string'">
              <v-col cols="6">
                <v-text-field
                  label="Min length"
                  :model-value="selectedNode.minLength ?? ''"
                  type="number"
                  @update:model-value="updateSelectedNode((node) => ({ ...node, minLength: $event ? Number($event) : null }))"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  label="Max length"
                  :model-value="selectedNode.maxLength ?? ''"
                  type="number"
                  @update:model-value="updateSelectedNode((node) => ({ ...node, maxLength: $event ? Number($event) : null }))"
                />
              </v-col>
            </v-row>

            <v-row v-if="selectedNode.type === 'integer' || selectedNode.type === 'number'">
              <v-col cols="6">
                <v-text-field
                  label="Minimum"
                  :model-value="selectedNode.minimum ?? ''"
                  type="number"
                  @update:model-value="updateSelectedNode((node) => ({ ...node, minimum: $event ? Number($event) : null }))"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  label="Maximum"
                  :model-value="selectedNode.maximum ?? ''"
                  type="number"
                  @update:model-value="updateSelectedNode((node) => ({ ...node, maximum: $event ? Number($event) : null }))"
                />
              </v-col>
            </v-row>

            <v-row v-if="selectedNode.type === 'array'">
              <v-col cols="6">
                <v-text-field
                  label="Min items"
                  :model-value="selectedNode.minItems ?? ''"
                  type="number"
                  @update:model-value="updateSelectedNode((node) => ({ ...node, minItems: $event ? Number($event) : null }))"
                />
              </v-col>
              <v-col cols="6">
                <v-text-field
                  label="Max items"
                  :model-value="selectedNode.maxItems ?? ''"
                  type="number"
                  @update:model-value="updateSelectedNode((node) => ({ ...node, maxItems: $event ? Number($event) : null }))"
                />
              </v-col>
            </v-row>

            <v-textarea
              v-if="selectedNode.type === 'enum'"
              auto-grow
              label="Enum options"
              :model-value="selectedNode.enumValues.join('\n')"
              rows="4"
              @update:model-value="updateEnumValues(String($event ?? ''))"
            />

            <template v-if="scope === 'response' && selectedNode.mode === 'fixed'">
              <v-switch
                v-if="selectedNode.type === 'boolean'"
                color="accent"
                inset
                label="Fixed boolean value"
                :model-value="Boolean(selectedNode.fixedValue)"
                @update:model-value="updateSelectedNode((node) => ({ ...node, fixedValue: Boolean($event) }))"
              />

              <v-text-field
                v-else-if="selectedNode.type === 'integer' || selectedNode.type === 'number'"
                label="Fixed value"
                :model-value="selectedNode.fixedValue"
                type="number"
                @update:model-value="updateSelectedNode((node) => ({ ...node, fixedValue: Number($event ?? 0) }))"
              />

              <v-textarea
                v-else-if="selectedNode.type === 'string' || selectedNode.type === 'enum'"
                auto-grow
                label="Fixed value"
                :model-value="String(selectedNode.fixedValue ?? '')"
                rows="3"
                @update:model-value="updateSelectedNode((node) => ({ ...node, fixedValue: String($event ?? '') }))"
              />

              <v-textarea
                v-else
                auto-grow
                :error-messages="fixedJsonError ?? undefined"
                label="Fixed JSON value"
                :model-value="fixedJsonDraft"
                rows="6"
                @update:model-value="updateStructuredFixedValue(String($event ?? ''))"
              />
            </template>

            <div v-if="selectedCanAcceptChildren" class="d-flex flex-column ga-3">
              <div class="text-overline text-medium-emphasis">Quick add</div>
              <div class="d-flex flex-wrap ga-2">
                <v-chip
                  v-for="item in PALETTE_TYPES"
                  :key="`quick-${item.type}`"
                  color="secondary"
                  label
                  variant="tonal"
                  @click="commitTree(addNodeToContainer(tree, selectedNode.id, item.type, scope))"
                >
                  {{ item.label }}
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>
    </v-col>

    <v-col cols="12" xl="5" lg="5">
      <v-card class="workspace-card fill-height">
        <v-card-item>
          <template #prepend>
            <v-avatar color="primary" variant="tonal">
              <v-icon icon="mdi-vector-polyline-plus" />
            </v-avatar>
          </template>

          <v-card-title>Canvas</v-card-title>
          <v-card-subtitle>
            Build the {{ scope }} payload visually with clear reorder and nesting drop zones.
          </v-card-subtitle>

          <template #append>
            <div class="d-flex flex-wrap ga-2">
              <v-btn prepend-icon="mdi-upload-outline" variant="text" @click="importDialog = true">
                Import
              </v-btn>
              <v-btn prepend-icon="mdi-content-copy" variant="text" @click="copySchema">
                Copy JSON
              </v-btn>
            </div>
          </template>
        </v-card-item>

        <v-divider />

        <v-card-text class="schema-canvas">
          <SchemaNodeCard
            :active-node-id="selectedNodeId"
            :node="tree"
            :parent-id="null"
            :parent-type="null"
            root
            :scope="scope"
            @drop-container="handleDropOnContainer"
            @drop-row="handleDropAfterRow"
            @select="selectedNodeId = $event"
            @start-drag="startNodeDrag"
          />
        </v-card-text>
      </v-card>
    </v-col>

    <v-col cols="12" xl="4" lg="4">
      <div class="d-flex flex-column ga-4">
        <v-card v-if="scope === 'response'" class="workspace-card">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon icon="mdi-lightning-bolt-outline" />
              </v-avatar>
            </template>

            <v-card-title>Generated preview</v-card-title>
            <v-card-subtitle>
              {{ normalizedSeedKey ? "Seeded preview stays deterministic." : "Preview refreshes with new random samples." }}
            </v-card-subtitle>

            <template #append>
              <v-btn
                v-if="!normalizedSeedKey"
                prepend-icon="mdi-refresh"
                variant="text"
                @click="runPreview(true)"
              >
                Regenerate
              </v-btn>
            </template>
          </v-card-item>

          <v-divider />

          <v-card-text>
            <v-chip color="secondary" label size="small" variant="tonal" class="mb-4">
              {{ previewModeLabel(selectedNode.mode) }}
            </v-chip>

            <v-skeleton-loader v-if="previewStatus === 'loading'" type="paragraph, paragraph, paragraph" />

            <v-alert v-else-if="previewStatus === 'error' && previewError" border="start" color="error" variant="tonal">
              {{ previewError }}
            </v-alert>

            <pre v-else class="code-block">{{ previewBody }}</pre>
          </v-card-text>
        </v-card>

        <v-card v-else class="workspace-card">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon icon="mdi-code-json" />
              </v-avatar>
            </template>

            <v-card-title>Schema preview</v-card-title>
            <v-card-subtitle>Review the request payload contract as live JSON Schema.</v-card-subtitle>
          </v-card-item>
          <v-divider />
          <v-card-text class="d-flex flex-column ga-4">
            <v-alert border="start" color="info" variant="tonal">
              Request authoring currently targets JSON request bodies. Query and path parameter modeling is still a later
              follow-up.
            </v-alert>

            <pre class="code-block">{{ JSON.stringify(liveSchema, null, 2) }}</pre>
          </v-card-text>
        </v-card>
      </div>
    </v-col>
  </v-row>

  <v-dialog v-model="importDialog" max-width="720">
    <v-card class="workspace-card">
      <v-card-item>
        <v-card-title>Import schema</v-card-title>
        <v-card-subtitle>Paste a JSON Schema object and the studio will normalize it into the builder tree.</v-card-subtitle>
      </v-card-item>
      <v-divider />
      <v-card-text class="d-flex flex-column ga-4">
        <v-alert v-if="importError" border="start" color="error" variant="tonal">
          {{ importError }}
        </v-alert>
        <v-textarea v-model="importText" auto-grow label="Schema JSON" rows="12" />
      </v-card-text>
      <v-card-actions class="px-6 pb-6">
        <v-spacer />
        <v-btn variant="text" @click="importDialog = false">Cancel</v-btn>
        <v-btn color="primary" prepend-icon="mdi-upload-outline" @click="importSchema">
          Import schema
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.schema-sidebar {
  width: 100%;
  min-height: 0;
  overscroll-behavior: contain;
}

.schema-sidebar > * {
  flex: 0 0 auto;
}

@media (min-width: 1280px) {
  .schema-sidebar-col {
    display: flex;
    position: sticky;
    top: 0;
    align-self: flex-start;
  }

  .schema-sidebar {
    height: calc(100vh - var(--v-layout-top, 88px) - 3rem);
    max-height: calc(100vh - var(--v-layout-top, 88px) - 3rem);
    overflow-y: auto;
    overflow-x: hidden;
    padding-right: 0.35rem;
    padding-bottom: 0.35rem;
    scrollbar-gutter: stable;
  }
}
</style>
