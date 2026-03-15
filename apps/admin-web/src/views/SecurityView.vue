<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  AdminApiError,
  changePassword,
  createAdminUser,
  deleteAdminUser,
  listAdminUsers,
  updateAdminUser,
} from "../api/admin";
import { useAuth } from "../composables/useAuth";
import type { AdminUser } from "../types/endpoints";

const auth = useAuth();
const router = useRouter();

const passwordForm = reactive({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});
const passwordBusy = ref(false);
const passwordError = ref<string | null>(null);
const passwordSuccess = ref<string | null>(null);

const users = ref<AdminUser[]>([]);
const usersLoading = ref(false);
const usersError = ref<string | null>(null);
const usersSuccess = ref<string | null>(null);

const createForm = reactive({
  username: "",
  password: "",
  isActive: true,
  isSuperuser: false,
  mustChangePassword: true,
});
const createBusy = ref(false);
const createError = ref<string | null>(null);

const editDialog = ref(false);
const editBusy = ref(false);
const editError = ref<string | null>(null);
const editForm = reactive({
  id: 0,
  username: "",
  password: "",
  isActive: true,
  isSuperuser: false,
  mustChangePassword: false,
});

const currentUserId = computed(() => auth.user.value?.id ?? null);
const canManageUsers = computed(() => auth.isSuperuser.value && !auth.mustChangePassword.value);

function describeError(error: unknown, fallbackMessage: string): string {
  return error instanceof Error ? error.message : fallbackMessage;
}

function handleExpiredSession(error: unknown, message: string): boolean {
  if (error instanceof AdminApiError && error.status === 401) {
    void auth.logout(message);
    void router.push({ name: "login" });
    return true;
  }

  return false;
}

async function loadUsers(): Promise<void> {
  if (!auth.session.value || !canManageUsers.value) {
    users.value = [];
    usersError.value = null;
    return;
  }

  usersLoading.value = true;
  usersError.value = null;

  try {
    users.value = await listAdminUsers(auth.session.value);
  } catch (error) {
    if (handleExpiredSession(error, "Your admin session expired. Sign in again before managing users.")) {
      return;
    }

    usersError.value = describeError(error, "Unable to load dashboard users.");
  } finally {
    usersLoading.value = false;
  }
}

watch(
  () => [auth.session.value?.token, canManageUsers.value],
  () => {
    void loadUsers();
  },
  { immediate: true },
);

async function submitPasswordChange(): Promise<void> {
  if (!auth.session.value) {
    passwordError.value = "Sign in again before changing your password.";
    return;
  }

  passwordError.value = null;
  passwordSuccess.value = null;

  if (!passwordForm.currentPassword || !passwordForm.newPassword) {
    passwordError.value = "Enter your current password and a new password.";
    return;
  }

  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    passwordError.value = "The new password confirmation does not match.";
    return;
  }

  passwordBusy.value = true;

  try {
    const snapshot = await changePassword(
      {
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      },
      auth.session.value,
    );
    auth.updateCurrentSession(snapshot);
    passwordForm.currentPassword = "";
    passwordForm.newPassword = "";
    passwordForm.confirmPassword = "";
    passwordSuccess.value = "Your password has been updated.";
    await loadUsers();
  } catch (error) {
    if (handleExpiredSession(error, "Your admin session expired. Sign in again before changing your password.")) {
      return;
    }

    passwordError.value = describeError(error, "Unable to change your password.");
  } finally {
    passwordBusy.value = false;
  }
}

async function submitCreateUser(): Promise<void> {
  if (!auth.session.value) {
    createError.value = "Sign in again before creating users.";
    return;
  }

  createError.value = null;
  usersSuccess.value = null;

  if (!createForm.username.trim() || !createForm.password) {
    createError.value = "Enter both a username and an initial password.";
    return;
  }

  createBusy.value = true;

  try {
    await createAdminUser(
      {
        username: createForm.username.trim(),
        password: createForm.password,
        is_active: createForm.isActive,
        is_superuser: createForm.isSuperuser,
        must_change_password: createForm.mustChangePassword,
      },
      auth.session.value,
    );
    createForm.username = "";
    createForm.password = "";
    createForm.isActive = true;
    createForm.isSuperuser = false;
    createForm.mustChangePassword = true;
    usersSuccess.value = "Created the new dashboard user.";
    await loadUsers();
  } catch (error) {
    if (handleExpiredSession(error, "Your admin session expired. Sign in again before creating users.")) {
      return;
    }

    createError.value = describeError(error, "Unable to create the dashboard user.");
  } finally {
    createBusy.value = false;
  }
}

function openEditDialog(user: AdminUser): void {
  editError.value = null;
  editForm.id = user.id;
  editForm.username = user.username;
  editForm.password = "";
  editForm.isActive = user.is_active;
  editForm.isSuperuser = user.is_superuser;
  editForm.mustChangePassword = user.must_change_password;
  editDialog.value = true;
}

async function submitUserUpdate(): Promise<void> {
  if (!auth.session.value) {
    editError.value = "Sign in again before saving user changes.";
    return;
  }

  editError.value = null;
  usersSuccess.value = null;
  editBusy.value = true;

  try {
    const updatedUser = await updateAdminUser(
      editForm.id,
      {
        username: editForm.username.trim(),
        password: editForm.password.trim() || undefined,
        is_active: editForm.isActive,
        is_superuser: editForm.isSuperuser,
        must_change_password: editForm.mustChangePassword,
      },
      auth.session.value,
    );
    if (updatedUser.id === currentUserId.value) {
      auth.updateCurrentUser(updatedUser);
    }
    editDialog.value = false;
    usersSuccess.value = `Saved ${updatedUser.username}.`;
    await loadUsers();
  } catch (error) {
    if (handleExpiredSession(error, "Your admin session expired. Sign in again before saving user changes.")) {
      return;
    }

    editError.value = describeError(error, "Unable to save the dashboard user.");
  } finally {
    editBusy.value = false;
  }
}

async function removeUser(): Promise<void> {
  if (!auth.session.value) {
    editError.value = "Sign in again before deleting users.";
    return;
  }

  const targetUser = users.value.find((user) => user.id === editForm.id);
  if (!targetUser) {
    editError.value = "Select a user before deleting.";
    return;
  }

  const shouldDelete = window.confirm(`Delete "${targetUser.username}" from the admin dashboard?`);
  if (!shouldDelete) {
    return;
  }

  editBusy.value = true;
  editError.value = null;

  try {
    await deleteAdminUser(targetUser.id, auth.session.value);
    editDialog.value = false;
    usersSuccess.value = `Deleted ${targetUser.username}.`;
    await loadUsers();
  } catch (error) {
    if (handleExpiredSession(error, "Your admin session expired. Sign in again before deleting users.")) {
      return;
    }

    editError.value = describeError(error, "Unable to delete the dashboard user.");
  } finally {
    editBusy.value = false;
  }
}
</script>

<template>
  <div class="d-flex flex-column ga-4">
    <div class="d-flex flex-column flex-lg-row justify-space-between ga-4">
      <div>
        <div class="text-overline text-secondary">Security and access</div>
        <div class="text-h3 font-weight-bold mt-2">Protect the private side of Mockingbird</div>
        <div class="text-body-1 text-medium-emphasis mt-3">
          Rotate your own password, manage dashboard users, and keep the admin studio separate from the public mock surface.
        </div>
      </div>

      <div class="d-flex flex-wrap align-start justify-end ga-2">
        <v-chip color="secondary" label variant="tonal">
          {{ auth.user.value?.is_superuser ? "Superuser" : "Editor" }}
        </v-chip>
        <v-chip v-if="auth.mustChangePassword.value" color="warning" label variant="tonal">
          Password change required
        </v-chip>
      </div>
    </div>

    <v-alert
      v-if="auth.mustChangePassword.value"
      border="start"
      color="warning"
      variant="tonal"
    >
      This account is still using a bootstrap or reset password. Change it now before the rest of the admin API unlocks.
    </v-alert>

    <v-row class="workspace-grid">
      <v-col cols="12" lg="5">
        <v-card class="workspace-card">
          <v-card-item>
            <template #prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon icon="mdi-lock-reset" />
              </v-avatar>
            </template>

            <v-card-title>Change your password</v-card-title>
            <v-card-subtitle>Sessions store tokens now, not raw passwords, so password rotation is safer and simpler.</v-card-subtitle>
          </v-card-item>

          <v-divider />

          <v-card-text class="d-flex flex-column ga-4">
            <v-alert v-if="passwordSuccess" border="start" color="success" variant="tonal">
              {{ passwordSuccess }}
            </v-alert>

            <v-alert v-if="passwordError" border="start" color="error" variant="tonal">
              {{ passwordError }}
            </v-alert>

            <v-text-field
              v-model="passwordForm.currentPassword"
              autocomplete="current-password"
              label="Current password"
              prepend-inner-icon="mdi-lock-outline"
              type="password"
            />

            <v-text-field
              v-model="passwordForm.newPassword"
              autocomplete="new-password"
              label="New password"
              prepend-inner-icon="mdi-lock-plus-outline"
              type="password"
            />

            <v-text-field
              v-model="passwordForm.confirmPassword"
              autocomplete="new-password"
              label="Confirm new password"
              prepend-inner-icon="mdi-lock-check-outline"
              type="password"
            />

            <v-btn
              color="primary"
              :loading="passwordBusy"
              prepend-icon="mdi-content-save-outline"
              @click="submitPasswordChange"
            >
              Save password
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="7">
        <v-card class="workspace-card">
          <v-card-item>
            <template #prepend>
              <v-avatar color="secondary" variant="tonal">
                <v-icon icon="mdi-account-multiple-outline" />
              </v-avatar>
            </template>

            <v-card-title>Dashboard users</v-card-title>
            <v-card-subtitle>Superusers can create, disable, and reset access for private studio accounts.</v-card-subtitle>
          </v-card-item>

          <v-divider />

          <v-card-text class="d-flex flex-column ga-4">
            <v-alert v-if="usersSuccess" border="start" color="success" variant="tonal">
              {{ usersSuccess }}
            </v-alert>

            <v-alert v-if="usersError" border="start" color="error" variant="tonal">
              {{ usersError }}
            </v-alert>

            <v-alert v-if="!auth.isSuperuser.value" border="start" color="info" variant="tonal">
              Your account can manage endpoints, but only superusers can invite or edit dashboard users.
            </v-alert>

            <v-alert
              v-else-if="auth.mustChangePassword.value"
              border="start"
              color="info"
              variant="tonal"
            >
              User management unlocks after you finish rotating this account&apos;s password.
            </v-alert>

            <template v-else>
              <div class="journey-panel d-flex flex-column ga-4">
                <div class="text-subtitle-1 font-weight-medium">Add a dashboard user</div>

                <v-text-field
                  v-model="createForm.username"
                  autocomplete="username"
                  label="Username"
                  prepend-inner-icon="mdi-account-outline"
                />

                <v-text-field
                  v-model="createForm.password"
                  autocomplete="new-password"
                  label="Initial password"
                  prepend-inner-icon="mdi-lock-plus-outline"
                  type="password"
                />

                <div class="d-flex flex-wrap ga-4">
                  <v-switch v-model="createForm.isActive" color="accent" inset label="Active account" />
                  <v-switch v-model="createForm.isSuperuser" color="secondary" inset label="Superuser" />
                  <v-switch
                    v-model="createForm.mustChangePassword"
                    color="warning"
                    inset
                    label="Require password reset"
                  />
                </div>

                <v-alert v-if="createError" border="start" color="error" variant="tonal">
                  {{ createError }}
                </v-alert>

                <div class="d-flex justify-end">
                  <v-btn color="secondary" :loading="createBusy" prepend-icon="mdi-account-plus-outline" @click="submitCreateUser">
                    Create user
                  </v-btn>
                </div>
              </div>

              <v-skeleton-loader
                v-if="usersLoading"
                type="table-heading, table-row-divider, table-row-divider, table-row-divider"
              />

              <div v-else class="journey-panel pa-0 overflow-hidden">
                <v-table density="comfortable">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Role</th>
                      <th>Status</th>
                      <th>Password</th>
                      <th class="text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="user in users" :key="user.id">
                      <td>
                        <div class="font-weight-medium">{{ user.username }}</div>
                        <div class="text-caption text-medium-emphasis">
                          {{ user.id === currentUserId ? "Current account" : "Dashboard user" }}
                        </div>
                      </td>
                      <td>
                        <v-chip :color="user.is_superuser ? 'secondary' : 'primary'" label size="small" variant="tonal">
                          {{ user.is_superuser ? "Superuser" : "Editor" }}
                        </v-chip>
                      </td>
                      <td>
                        <v-chip :color="user.is_active ? 'accent' : 'surface-variant'" label size="small" variant="tonal">
                          {{ user.is_active ? "Active" : "Disabled" }}
                        </v-chip>
                      </td>
                      <td>
                        <v-chip :color="user.must_change_password ? 'warning' : 'success'" label size="small" variant="tonal">
                          {{ user.must_change_password ? "Reset required" : "Up to date" }}
                        </v-chip>
                      </td>
                      <td class="text-right">
                        <v-btn density="comfortable" icon="mdi-pencil" variant="text" @click="openEditDialog(user)" />
                      </td>
                    </tr>
                  </tbody>
                </v-table>
              </div>
            </template>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="editDialog" max-width="640">
      <v-card class="workspace-card">
        <v-card-item>
          <template #prepend>
            <v-avatar color="info" variant="tonal">
              <v-icon icon="mdi-account-cog-outline" />
            </v-avatar>
          </template>

          <v-card-title>Edit dashboard user</v-card-title>
          <v-card-subtitle>Update access level, activation state, or issue a reset password.</v-card-subtitle>
        </v-card-item>

        <v-divider />

        <v-card-text class="d-flex flex-column ga-4">
          <v-alert v-if="editError" border="start" color="error" variant="tonal">
            {{ editError }}
          </v-alert>

          <v-text-field
            v-model="editForm.username"
            autocomplete="username"
            label="Username"
            prepend-inner-icon="mdi-account-outline"
          />

          <v-text-field
            v-model="editForm.password"
            autocomplete="new-password"
            label="Reset password"
            prepend-inner-icon="mdi-lock-plus-outline"
            type="password"
          />

          <div class="d-flex flex-wrap ga-4">
            <v-switch v-model="editForm.isActive" color="accent" inset label="Active account" />
            <v-switch v-model="editForm.isSuperuser" color="secondary" inset label="Superuser" />
            <v-switch
              v-model="editForm.mustChangePassword"
              color="warning"
              inset
              label="Require password reset"
            />
          </div>
        </v-card-text>

        <v-divider />

        <v-card-actions class="px-6 py-4 d-flex justify-space-between">
          <v-btn color="error" prepend-icon="mdi-delete-outline" variant="text" @click="removeUser">
            Delete
          </v-btn>
          <div class="d-flex ga-2">
            <v-btn variant="text" @click="editDialog = false">Cancel</v-btn>
            <v-btn color="primary" :loading="editBusy" prepend-icon="mdi-content-save-outline" @click="submitUserUpdate">
              Save changes
            </v-btn>
          </div>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
