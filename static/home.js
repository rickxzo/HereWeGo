const DeploymentTemplates = {
  props: ["repos"],

  template: `
    <div class="pt-36 px-5 pb-10">

      <!-- Header -->
      <div class="mb-6">

        <h2 class="text-2xl font-bold text-white">
          Deployment Templates
        </h2>

        <p class="text-zinc-500 text-sm mt-1">
          Existing deployment configurations
        </p>

      </div>

      <!-- Empty State -->
      <div
        v-if="repos.length === 0"
        class="bg-zinc-900 border border-zinc-800 rounded-3xl p-10 text-center"
      >

        <p class="text-zinc-400">
          No deployment templates found
        </p>

      </div>

      <!-- Grid -->
      <div
        v-else
        class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5"
      >

        <div
          v-for="repo in repos"
          :key="repo.id"
          class="bg-zinc-900 border border-zinc-800 rounded-3xl p-5 hover:border-zinc-700 transition"
        >

          <!-- Top -->
          <div class="flex items-start justify-between gap-4">

            <div class="min-w-0">

              <h3 class="text-lg font-semibold text-white truncate">
                {{ repo.name }}
              </h3>

              <p class="text-zinc-500 text-sm mt-1 truncate">
                ID: {{ repo.id }}
              </p>

            </div>

            <div
              class="text-xs px-3 py-1 rounded-xl whitespace-nowrap border capitalize"
              :class="repo.status
                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
                : 'bg-zinc-800 border-zinc-700 text-zinc-400'"
            >
              {{ repo.status || "Inactive" }}
            </div>

          </div>

          <!-- Commands -->
          <div class="mt-5 space-y-4">

            <!-- Build -->
            <div>

              <p class="text-zinc-500 text-xs mb-2">
                Build Command
              </p>

              <div class="bg-black/40 border border-zinc-800 rounded-2xl px-4 py-3 text-sm text-zinc-200 font-mono overflow-x-auto">
                {{ repo.build_cmd || "N/A" }}
              </div>

            </div>

            <!-- Run -->
            <div>

              <p class="text-zinc-500 text-xs mb-2">
                Run Command
              </p>

              <div class="bg-black/40 border border-zinc-800 rounded-2xl px-4 py-3 text-sm text-zinc-200 font-mono overflow-x-auto">
                {{ repo.run_cmd || "N/A" }}
              </div>

            </div>
            <div>

              <p class="text-zinc-500 text-xs mb-2">
                Link
              </p>

              <div class="bg-black/40 border border-zinc-800 rounded-2xl px-4 py-3 text-sm text-zinc-200 font-mono overflow-x-auto">
                {{ repo.status === "running" ? repo.link : "Not deployed" }}
              </div>

            </div>
            <!-- Actions -->
            <!-- Actions -->
            <div class="grid grid-cols-4 gap-3 pt-2">

              <!-- Logs -->
              <button
                @click="repo.status === 'running' ? rollbackRepo(repo) : deployRepo(repo)"
                :disabled="deployingRepoId === repo.id"
                class="bg-zinc-800 hover:bg-zinc-700 border border-zinc-700 text-white py-3 rounded-2xl transition text-sm font-medium disabled:opacity-50"
              >
                {{
                  deployingRepoId === repo.id
                    ? (repo.status === 'running' ? "Rolling back..." : "Deploying...")
                    : (repo.status === 'running' ? "Rollback" : "Deploy")
                }}
              </button>

              <button
                @click="openLogs(repo.deploy_id)"
                :disabled="!repo.deploy_id"
                class="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm transition"
              >
                Logs
              </button>

              <!-- Edit -->
              <button
                class="bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 text-blue-300 py-3 rounded-2xl transition text-sm font-medium"
              >
                Edit
              </button>

              <!-- Delete -->
              <div class="relative group">
  
                <button
                  @click="repo.status !== 'running' && deleteRepo(repo)"
                  :disabled="repo.status === 'running' || deleting"
                  class="w-full bg-red-500/10 border border-red-500/20 text-red-400 py-3 rounded-2xl transition text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
                  :class="repo.status !== 'running' ? 'hover:bg-red-500/20' : ''"
                >
                  Delete
                </button>

                <div
                  v-if="repo.status === 'running'"
                  class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 whitespace-nowrap bg-zinc-900 border border-zinc-700 text-zinc-300 text-xs px-3 py-2 rounded-xl opacity-0 group-hover:opacity-100 pointer-events-none transition z-50"
                >
                  Repository can only be deleted after rollback
                </div>

              </div>

              <div
                v-if="logsModalOpen"
                class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
              >
                <div class="w-full max-w-5xl h-[80vh] bg-[#0b0f19] border border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
                  
                  <!-- Header -->
                  <div class="flex items-center justify-between px-6 py-4 border-b border-slate-800">
                    <div class="flex items-center gap-3">
                      <div class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                      <h2 class="text-slate-100 font-semibold text-lg">
                        Deployment Logs
                      </h2>
                    </div>

                    <div class="flex items-center gap-3">
                      <button
                        @click="fetchLogs"
                        class="text-sm px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                      >
                        Refresh
                      </button>

                      <button
                        @click="closeLogs"
                        class="text-slate-400 hover:text-white text-xl leading-none"
                      >
                        ×
                      </button>
                    </div>
                  </div>

                  <!-- Logs Body -->
                  <div
                    ref="logsContainer"
                    class="flex-1 overflow-y-auto p-5 font-mono text-sm text-emerald-300 whitespace-pre-wrap break-words"
                  >
                    <template v-if="loadingLogs">
                      <div class="text-slate-400">Loading logs...</div>
                    </template>

                    <template v-else>
                      {{ logsContent || 'No logs available.' }}
                    </template>
                  </div>
                </div>
              </div>

            </div>

          </div>

        </div>

      </div>

    </div>
  `,
  data() {
    return {
      deployLoading: false,
      deployingRepoId: null,
      deleting: false,
      logsModalOpen: false,
      logsContent: "",
      loadingLogs: false,
      currentDeploymentId: null,
      logsInterval: null,
    };
  },
  methods: {
    async deleteRepo(repo) {
      try {
        this.deleting = true;
        const token = localStorage.getItem("token");
        const response = await fetch(`/api/delete-repo?repo_id=${repo.id}`,
          {
            method: 'GET',
            headers: {
              Authorization: `Bearer ${token}`
            }
          }
        );

        if (!response.ok){
          let errorMessage = "Failed to deploy";

          try {

            const errorData = await response.json();

            errorMessage =
              errorData.detail ||
              JSON.stringify(errorData);

          } catch (_) {}

          throw new Error(errorMessage);
        }

        this.$emit("refresh-repos");

      } catch (err) {
        console.error(err);
      }


    },
    async deployRepo(repo) {

      try {

        this.deployingRepoId = repo.id;

        const token = localStorage.getItem("token");

        const response = await fetch(
          `/api/deploy?repo_id=${repo.id}`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`
            }
          }
        );

        if (!response.ok) {

          let errorMessage = "Failed to deploy";

          try {

            const errorData = await response.json();

            errorMessage =
              errorData.detail ||
              JSON.stringify(errorData);

          } catch (_) {}

          throw new Error(errorMessage);
        }

        const data = await response.json();

        /*
          OPTION 1:
          Update frontend instantly
        */

        repo.status = data.status;
        repo.link = data.url;
        repo.deployment_id = data.deployment_id;

        /*
          OPTION 2 (better):
          Re-fetch repos from backend
          so frontend always stays synced
        */

        this.$emit("refresh-repos");

      } catch (err) {

        console.error(err);

      } finally {

        this.deployingRepoId = null;

      }
    },
    async rollbackRepo(repo) {

      try {

        this.deployingRepoId = repo.id;

        const token = localStorage.getItem("token");

        const response = await fetch(
          `/api/rollback?deployment_id=${repo.deploy_id}`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`
            }
          }
        );

        if (!response.ok) {

          let errorMessage = "Failed to rollback";

          try {

            const errorData = await response.json();

            errorMessage =
              errorData.detail ||
              JSON.stringify(errorData);

          } catch (_) {}

          throw new Error(errorMessage);
        }

        this.$emit("refresh-repos");

      } catch (err) {

        console.error(err);

      } finally {

        this.deployingRepoId = null;

      }
    },

    async openLogs(deploymentId) {
      this.currentDeploymentId = deploymentId;
      this.logsModalOpen = true;

      await this.fetchLogs();

      // Poll every 10 seconds
      this.logsInterval = setInterval(() => {
        this.fetchLogs();
      }, 10000);
    },

    closeLogs() {
      this.logsModalOpen = false;
      this.logsContent = "";
      this.currentDeploymentId = null;

      if (this.logsInterval) {
        clearInterval(this.logsInterval);
        this.logsInterval = null;
      }
    },

    async fetchLogs() {
      
      if (!this.currentDeploymentId) return;
      const token = localStorage.getItem("token");
      try {
        this.loadingLogs = true;

        const response = await fetch(
          `/api/logs?deployment_id=${this.currentDeploymentId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        const data = await response.json();

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(data?.detail || "Failed to fetch logs");
        }


        this.logsContent = data.logs || "";

        this.$nextTick(() => {
          const container = this.$refs.logsContainer;

          if (container) {
            container.scrollTop = container.scrollHeight;
          }
        });
      } catch (error) {
        console.error("Failed to fetch logs:", error);
        this.logsContent = "Failed to load logs.";
      } finally {
        this.loadingLogs = false;
      }
    },
  },

  beforeUnmount() {
    if (this.logsInterval) {
      clearInterval(this.logsInterval);
    }
  }
};













const GithubLoginPage = {
  template: `
    <div class="min-h-screen bg-black text-white">

      <!-- TOP BAR AFTER LOGIN -->
      <div
        v-if="user.id"
        class="fixed top-5 left-5 right-5 flex items-center justify-between z-50"
      >

        <!-- USER TAB -->
        <div class="bg-zinc-900/95 border border-zinc-800 rounded-2xl px-4 py-3 flex items-center gap-4 shadow-2xl backdrop-blur">

          <!-- Avatar -->
          <img
            :src="user.avatar"
            class="w-11 h-11 rounded-xl object-cover border border-zinc-700"
          />

          <!-- User Info -->
          <div>
            <h2 class="text-sm font-semibold leading-tight">
              {{ user.username }}
            </h2>

            <div class="mt-1 inline-flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-emerald-400"></div>

              <span class="text-emerald-300 text-xs">
                Connected
              </span>
            </div>
          </div>

          <!-- Divider -->
          <div class="h-10 w-px bg-zinc-800 mx-1"></div>

          <!-- Logout -->
          <button
            @click="logout"
            class="text-red-400 text-sm px-3 py-2 rounded-xl hover:bg-red-500/10 transition"
          >
            Logout
          </button>

        </div>

        <!-- REPO SELECT -->
        <div class="relative w-full max-w-md ml-5">

          <input
            v-model="repoSearch"
            @focus="dropdownOpen = true"
            type="text"
            placeholder="Search repositories..."
            class="w-full bg-zinc-900/95 border border-zinc-800 rounded-2xl px-5 py-3 outline-none focus:border-zinc-600 transition"
          />

          <!-- Dropdown -->
          <div
            v-if="dropdownOpen"
            class="absolute mt-2 w-full bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden max-h-72 overflow-y-auto"
          >

            <div
              v-for="repo in filteredRepos"
              :key="repo.id"
              class="px-4 py-3 border-b border-zinc-800/60 last:border-0 flex items-center justify-between gap-4"
            >

              <!-- Repo Info -->
              <div
                @click="selectRepo(repo)"
                class="cursor-pointer flex-1 min-w-0"
              >

                <p class="font-medium text-sm truncate">
                  {{ repo.name }}
                </p>

                <p class="text-zinc-500 text-xs mt-1 truncate">
                  {{ repo.full_name }}
                </p>

              </div>

              <!-- Deploy Button -->
              <button
                @click.stop="openDeploymentModal(repo)"
                class="bg-white text-black text-xs font-medium px-4 py-2 rounded-xl hover:scale-[1.02] transition"
              >
                Create Deployment
              </button>

            </div>

            <div
              v-if="filteredRepos.length === 0"
              class="px-4 py-4 text-zinc-500 text-sm"
            >
              No repositories found
            </div>

          </div>

        </div>

      </div>

      <!-- DEPLOYMENTS -->
      <deployment-templates
        v-if="user.id"
        :repos="repos"
        @refresh-repos="fetchRepos"
      ></deployment-templates>

      <!-- LOGIN SCREEN -->
      <div
        v-if="!user.id"
        class="min-h-screen flex items-center justify-center px-4"
      >

        <div class="w-full max-w-sm">

          <div class="bg-zinc-900/95 border border-zinc-800 rounded-3xl shadow-2xl overflow-hidden backdrop-blur">

            <div class="h-px bg-gradient-to-r from-transparent via-white/70 to-transparent"></div>

            <div class="p-7">

              <div class="flex justify-center mb-5">
                <div class="w-16 h-16 rounded-2xl bg-white flex items-center justify-center shadow-lg">
                  <img
                    src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
                    class="w-9 h-9"
                  />
                </div>
              </div>

              <div class="text-center mb-7">
                <h1 class="text-3xl font-bold tracking-tight text-white">
                  GitHub Login
                </h1>

                <p class="text-zinc-400 text-sm mt-2">
                  Connect your GitHub account
                </p>
              </div>

              <button
                @click="connectGithub"
                class="w-full bg-white text-black py-3.5 rounded-2xl font-semibold hover:scale-[1.01] active:scale-[0.99] transition-all duration-200"
              >
                Continue with GitHub
              </button>

            </div>

          </div>

        </div>

      </div>

      <!-- DEPLOYMENT MODAL -->
      <div
        v-if="deploymentModal"
        class="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-[100] px-4"
      >

        <div class="w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-3xl shadow-2xl overflow-hidden">

          <!-- Header -->
          <div class="px-6 py-5 border-b border-zinc-800">

            <div class="flex items-start justify-between gap-4">

              <div>
                <h2 class="text-xl font-bold">
                  Create Deployment
                </h2>

                <p class="text-zinc-500 text-sm mt-1">
                  {{ selectedDeploymentRepo?.full_name }}
                </p>
              </div>

              <button
                @click="deploymentModal = false"
                class="text-zinc-500 hover:text-white text-xl"
              >
                ×
              </button>

            </div>

          </div>

          <!-- Form -->
          <div class="p-6 space-y-5">

                <div>
                  <label class="block text-sm text-zinc-400 mb-2">
                    Preferred domain name
                  </label>
              
                  <input
                    v-model="deploymentForm.domain"
                    type="text"
                    placeholder="<domain>.herewego.website"
                    class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 outline-none focus:border-zinc-600 transition"
                  />
                </div>
              
                <div>
                  <label class="block text-sm text-zinc-400 mb-2">
                    Build Command
                  </label>
              
                  <input
                    v-model="deploymentForm.build"
                    type="text"
                    placeholder="npm install && npm run build"
                    class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 outline-none focus:border-zinc-600 transition"
                  />
                </div>
              
                <div>
                  <label class="block text-sm text-zinc-400 mb-2">
                    Run Command
                  </label>
              
                  <input
                    v-model="deploymentForm.run"
                    type="text"
                    placeholder="npm start"
                    class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 outline-none focus:border-zinc-600 transition"
                  />
                </div>
              
                <div>
                  <label class="block text-sm text-zinc-400 mb-2">
                    Environment Variables
                  </label>
              
                  <textarea
                    v-model="deploymentForm.env"
                    rows="7"
                    placeholder="SECRET1=ABC
              SECRET2=BDF
              DATABASE_URL=XYZ"
                    class="w-full bg-zinc-950 border border-zinc-800 rounded-2xl px-4 py-3 outline-none focus:border-zinc-600 transition resize-none"
                  ></textarea>
                </div>

                <div
              v-if="deployError"
              class="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-2xl text-sm"
            >
              {{ deployError }}
            </div>

            <div
              v-if="deploySuccess"
              class="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-4 py-3 rounded-2xl text-sm"
            >
              {{ deploySuccess }}
            </div>

            <button
              @click="createDeployment"
              :disabled="deployLoading"
              class="w-full bg-white text-black py-3 rounded-2xl font-semibold hover:scale-[1.01] active:scale-[0.99] transition disabled:opacity-50 disabled:hover:scale-100"
            >
              {{ deployButtonText }}
            </button>
              
              </div>

          </div>

        </div>

      </div>

    </div>
  `,

  data() {
    return {
      user: {
        id: "",
        username: "",
        avatar: ""
      },

      deploymentModal: false,
      deployButtonText: "Deploy Repository",

      selectedDeploymentRepo: null,

      deploymentForm: {
        build: "",
        run: "",
        env: "",
        domain: ""
      },

      deployLoading: false,
      deployError: "",
      deploySuccess: "",

      githubRepos: [],
      repos: [],

      repoSearch: "",
      dropdownOpen: false,
      selectedRepo: null
    };
  },

  computed: {
    filteredRepos() {
      return this.githubRepos.filter(repo =>
        repo.full_name.toLowerCase().includes(
          this.repoSearch.toLowerCase()
        )
      );
    }
  },

  methods: {
    
    connectGithub() {
      window.location.href = "/login/github";
    },

    logout() {
      localStorage.removeItem("token");
      localStorage.removeItem("github_user");

      this.user = {
        id: "",
        username: "",
        avatar: ""
      };

      this.githubRepos = [];
      this.repos = [];
    },

    async fetchGithubRepos() {

      try {

        const token = localStorage.getItem("token");

        const response = await fetch(
          "/api/github-repos",
          {
            headers: {
              Authorization: `Bearer ${token}`
            }
          }
        );

        const data = await response.json();

        this.githubRepos = data;

      } catch (err) {

        console.error("Failed to fetch repos:", err);

      }
    },

    async fetchRepos() {

      try {

        const token = localStorage.getItem("token");

        const response = await fetch(
          "/api/repos",
          {
            headers: {
              Authorization: `Bearer ${token}`
            }
          }
        );

        if (!response.ok) {
          throw new Error("Failed to fetch deployments");
        }

        const data = await response.json();

        this.repos = data;
        console.log(this.repos);

      } catch (err) {

        console.error(err);

      }
    },

    selectRepo(repo) {

      this.selectedRepo = repo;
      this.repoSearch = repo.full_name;
      this.dropdownOpen = false;

    },

    openDeploymentModal(repo) {

      this.selectedDeploymentRepo = repo;

      this.deploymentForm = {
        build: "",
        run: "",
        env: ""
      };

      this.deployError = "";
      this.deploySuccess = "";

      this.deploymentModal = true;
    },

    async createDeployment() {

      try {

        this.deployLoading = true;
        this.deployButtonText = "Creating deploy template";

        this.deployError = "";
        this.deploySuccess = "";

        const token = localStorage.getItem("token");

        const createResponse = await fetch(
          `/api/create-repo?repo_name=${encodeURIComponent(this.selectedDeploymentRepo.full_name)}&build=${encodeURIComponent(this.deploymentForm.build)}&run=${encodeURIComponent(this.deploymentForm.run)}&domain=${encodeURIComponent(this.deploymentForm.domain)}`,
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`
            }
          }
        );

        if (!createResponse.ok) {

          let errorMessage = "Failed to create deployment";

          try {

            const errorData = await createResponse.json();

            errorMessage =
              errorData.detail ||
              JSON.stringify(errorData);

          } catch (_) {}

          throw new Error(errorMessage);
        }

        const createData = await createResponse.json();

        const repoId = createData.repo_id;

        if (!repoId) {
          throw new Error("No repo ID returned");
        }

        this.deployButtonText =
          "Uploading environment variables";

        const secretsResponse = await fetch(
          `/api/add-secrets?repo_id=${repoId}`,
          {
            method: "POST",

            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "text/plain"
            },

            body: this.deploymentForm.env
          }
        );

        if (!secretsResponse.ok) {

          let errorMessage = "Failed to add secrets";

          try {

            const errorData = await secretsResponse.json();

            errorMessage =
              errorData.detail ||
              JSON.stringify(errorData);

          } catch (_) {}

          throw new Error(errorMessage);
        }

        this.deployButtonText = "Template created";

        this.deploySuccess =
          "Deployment template created successfully.";

        await this.fetchRepos();

        setTimeout(() => {

          this.deploymentModal = false;

          this.deployButtonText =
            "Deploy Repository";


        }, 3000);

      } catch (err) {

        console.error(err);

        this.deployError =
          err.message || "Something went wrong.";

      } finally {

        this.deployLoading = false;

      }
    }
  },

  async mounted() {

    const savedUser =
      localStorage.getItem("github_user");

    if (savedUser) {
      this.user = JSON.parse(savedUser);
    }

    const params =
      new URLSearchParams(window.location.search);

    const token = params.get("token");
    const id = params.get("id");
    const username = params.get("username");
    const avatar = params.get("avatar");

    if (token && id) {

      localStorage.setItem("token", token);

      const userData = {
        id,
        username,
        avatar
      };

      localStorage.setItem(
        "github_user",
        JSON.stringify(userData)
      );

      this.user = userData;

      window.history.replaceState(
        {},
        document.title,
        window.location.pathname
      );
    }

    if (this.user.id) {

      await this.fetchGithubRepos();
      await this.fetchRepos();

    }

    document.addEventListener("click", (e) => {

      const dropdown = e.target.closest(".relative");

      if (!dropdown) {
        this.dropdownOpen = false;
      }

    });
  }
};

const app = Vue.createApp({});

app.component(
  "github-login-page",
  GithubLoginPage
);

app.component(
  "deployment-templates",
  DeploymentTemplates
);

app.mount("#app");
