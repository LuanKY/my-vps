// Detecta host e porta automaticamente do navegador ou usa localhost:8000 como fallback
const hostWithPort = (typeof window !== "undefined" && window.location.host && window.location.host !== "")
  ? window.location.host
  : "localhost:8000";
const protocol = (typeof window !== "undefined" && window.location.protocol === "https:") ? "wss:" : "ws:";
const WS_URL = `${protocol}//${hostWithPort}/ws/data`;
let socket = null;
let reconnectTimer = null;
let lastDashboardData = null;
let currentConnectionState = "connecting";

// Sincronização do contador de próxima atualização (derivado de timestamps sem drift)
let updateIntervalSeconds = 3.0;
let lastUpdateMonotonic = null;
let countdownTimerId = null;

const translations = {
  en: {
    uptime_label: "uptime:",
    status_connecting: "connecting",
    status_connected: "connected",
    status_disconnected: "disconnected",
    load_avg_label: "load average:",
    load_avg_tooltip: "1m, 5m, 15m load average",
    next_update_title: "Next update in",
    memory_card_title: "MEMORY",
    swap_label: "swap:",
    disk_card_title: "DISK (/)",
    free_label: "free:",
    checking: "checking",
    running: "running",
    stopped: "stopped",
    status_running: "running",
    status_exited: "exited",
    status_paused: "paused",
    status_restarting: "restarting",
    status_created: "created",
    status_dead: "dead",
    containers_count: (n) => `containers: ${n} total`,
    total_badge: (n) => `${n} total`,
    disabled: "disabled",
    active: "active",
    inactive: "inactive",
    realtime: "realtime",
    waiting_metrics: "waiting for metrics...",
    no_interfaces: "no interfaces detected",
    no_cores: "no core metrics available",
    read: "read",
    write: "write",
    active_sessions: "active sessions:",
    th_name: "NAME",
    th_status: "STATUS",
    th_image: "IMAGE",
    th_container_id: "CONTAINER ID",
    th_ports: "PORTS",
    th_command: "COMMAND",
    cpu_cores_title: "CPU CORES",
    network_disk_title: "NETWORK & DISK I/O",
    docker_table_title: "DOCKER CONTAINERS",
    docker_unreachable: "Docker daemon unreachable or inactive.",
    no_running_containers: "No running containers.",
    top_processes_cpu: "Top Processes (CPU)",
    top_processes_memory: "Top Processes (Memory)",
    waiting_processes: "waiting for processes...",
    no_processes: "no processes found."
  },
  pt: {
    uptime_label: "tempo de atividade:",
    status_connecting: "conectando",
    status_connected: "conectado",
    status_disconnected: "desconectado",
    load_avg_label: "Média de carga:",
    load_avg_tooltip: "Média de carga em 1m, 5m, 15m",
    next_update_title: "Próxima atualização em",
    memory_card_title: "MEMÓRIA",
    swap_label: "swap:",
    disk_card_title: "DISCO (/)",
    free_label: "livre:",
    checking: "verificando",
    running: "em execução",
    stopped: "parado",
    status_running: "em execução",
    status_exited: "encerrado",
    status_paused: "pausado",
    status_restarting: "reiniciando",
    status_created: "criado",
    status_dead: "morto",
    containers_count: (n) => `contêineres: ${n} no total`,
    total_badge: (n) => `${n} no total`,
    disabled: "desativado",
    active: "ativo",
    inactive: "inativo",
    realtime: "tempo real",
    waiting_metrics: "aguardando métricas...",
    no_interfaces: "nenhuma interface detectada",
    no_cores: "nenhuma métrica de núcleos disponível",
    read: "leitura",
    write: "gravação",
    active_sessions: "sessões ativas:",
    th_name: "NOME",
    th_status: "STATUS",
    th_image: "IMAGEM",
    th_container_id: "CONTAINER ID",
    th_ports: "PORTAS",
    th_command: "COMANDO",
    cpu_cores_title: "NÚCLEOS DA CPU",
    network_disk_title: "REDE E I/O DE DISCO",
    docker_table_title: "CONTÊINERES DOCKER",
    docker_unreachable: "Daemon Docker inacessível ou inativo.",
    no_running_containers: "Nenhum contêiner em execução.",
    top_processes_cpu: "Principais Processos (CPU)",
    top_processes_memory: "Principais Processos (Memória)",
    waiting_processes: "aguardando processos...",
    no_processes: "nenhum processo encontrado."
  }
};

let currentLang = localStorage.getItem("myvps_lang") || ((typeof navigator !== "undefined" && navigator.language && navigator.language.startsWith("pt")) ? "pt" : "en");


function formatContainerStatus(statusStr, stateStr) {
  const raw = (statusStr || stateStr || "").trim();
  const lower = raw.toLowerCase();

  // Caso 1: corresponde diretamente ao estado conhecido (ex: "running", "exited", "paused")
  if (lower === "running") return t("status_running");
  if (lower === "exited") return t("status_exited");
  if (lower === "paused") return t("status_paused");
  if (lower === "restarting") return t("status_restarting");
  if (lower === "created") return t("status_created");
  if (lower === "dead") return t("status_dead");

  // Caso 2: c.status do docker-py vem no formato "Up 2 hours", "Exited (0) 5 minutes ago", etc.
  if (currentLang === "pt") {
    // Se começa com "Up", traduz para "Ativo" mantendo o restante ou se for apenas Up
    if (lower.startsWith("up")) {
      return raw.replace(/^Up\b/i, "Ativo");
    }
    if (lower.startsWith("exited")) {
      return raw.replace(/^Exited\b/i, "Encerrado");
    }
    if (lower.startsWith("restarting")) {
      return raw.replace(/^Restarting\b/i, "Reiniciando");
    }
    if (lower.startsWith("created")) {
      return raw.replace(/^Created\b/i, "Criado");
    }
    if (lower.startsWith("paused")) {
      return raw.replace(/^Paused\b/i, "Pausado");
    }
    if (lower.startsWith("dead")) {
      return raw.replace(/^Dead\b/i, "Morto");
    }
  }

  // Fallback para o valor original se não bater ou em en
  return raw || (stateStr ? (t(`status_${stateStr}`) || stateStr) : "-");
}

function t(key, ...args) {
  const dict = translations[currentLang] || translations.en;
  const val = dict[key] ?? translations.en[key] ?? key;
  if (typeof val === "function") {
    return val(...args);
  }
  return val;
}

function setLanguage(lang) {
  if (lang !== "en" && lang !== "pt") return;
  currentLang = lang;
  try {
    localStorage.setItem("myvps_lang", lang);
  } catch (e) {
    console.warn("Could not save language to localStorage:", e);
  }
  document.documentElement.lang = lang;
  updateLanguageUI();
}

function updateLanguageUI() {
  const btnEn = document.getElementById("lang-btn-en");
  const btnPt = document.getElementById("lang-btn-pt");

  if (btnEn && btnPt) {
    if (currentLang === "en") {
      btnEn.className = "px-2 py-0.5 rounded text-white bg-slate-800 font-semibold transition-colors";
      btnPt.className = "px-2 py-0.5 rounded text-slate-400 hover:text-white transition-colors";
    } else {
      btnPt.className = "px-2 py-0.5 rounded text-white bg-slate-800 font-semibold transition-colors";
      btnEn.className = "px-2 py-0.5 rounded text-slate-400 hover:text-white transition-colors";
    }
  }

  // Atualiza elementos com data-i18n
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (key) {
      el.textContent = t(key);
    }
  });

  // Atualiza tooltips traduzidos
  const cpuLoadContainer = document.getElementById("cpu-load-container");
  if (cpuLoadContainer) {
    cpuLoadContainer.title = t("load_avg_tooltip");
  }
  const nextUpdateCounterEl = document.getElementById("next-update-counter");
  if (nextUpdateCounterEl) {
    nextUpdateCounterEl.title = t("next_update_title");
  }

  // Atualiza conexão e dados atuais se houver
  updateStatus(currentConnectionState);
  if (lastDashboardData) {
    renderDashboard(lastDashboardData);
  }
}

// Elementos da UI
const statusPill = document.getElementById("status-pill");
const statusIndicator = document.getElementById("status-indicator");
const statusText = document.getElementById("status-text");
const lastUpdate = document.getElementById("last-update");
const nextUpdateCounter = document.getElementById("next-update-counter");
const uptimeDisplay = document.getElementById("uptime-display");

// Helper: Cores de status dev/sysadmin
function getStatusColor(percent) {
  if (percent === null || percent === undefined || isNaN(percent)) {
    return { text: "text-slate-400", bar: "bg-slate-700" };
  }
  if (percent >= 85) {
    return { text: "text-rose-400", bar: "bg-rose-400" };
  }
  if (percent >= 70) {
    return { text: "text-amber-300", bar: "bg-amber-400" };
  }
  return { text: "text-white", bar: "bg-emerald-400" };
}

// ==============================================================================
// Temporizador Preciso de Próxima Atualização
// Derivado monotonicamente de timestamps sem drift acumulativo e sincronizado
// com UPDATE_INTERVAL real da VPS.
// ==============================================================================

function tickCountdown() {
  if (!nextUpdateCounter) return;

  if (currentConnectionState !== "connected" || lastUpdateMonotonic === null) {
    nextUpdateCounter.textContent = "--";
    return;
  }

  const elapsed = (performance.now() - lastUpdateMonotonic) / 1000;
  const remaining = Math.max(0, updateIntervalSeconds - elapsed);
  nextUpdateCounter.textContent = `${remaining.toFixed(1)}s`;
}

function startCountdownTimer() {
  if (countdownTimerId) {
    clearInterval(countdownTimerId);
  }
  countdownTimerId = setInterval(tickCountdown, 100);
}

function stopCountdownTimer() {
  if (countdownTimerId) {
    clearInterval(countdownTimerId);
    countdownTimerId = null;
  }
  if (nextUpdateCounter) {
    nextUpdateCounter.textContent = "--";
  }
}

// Conectar ao WebSocket
function connectWebSocket() {
  clearTimeout(reconnectTimer);
  updateStatus("connecting");

  try {
    socket = new WebSocket(WS_URL);
  } catch (err) {
    console.error("WebSocket init error:", err);
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    updateStatus("connected");
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.update_interval && typeof data.update_interval === "number" && data.update_interval > 0) {
        updateIntervalSeconds = data.update_interval;
      }
      lastUpdateMonotonic = performance.now();
      lastDashboardData = data;
      renderDashboard(data);
      tickCountdown();
      if (!countdownTimerId) {
        startCountdownTimer();
      }
    } catch (err) {
      console.error("JSON parse error:", err);
    }
  };

  socket.onclose = () => {
    updateStatus("disconnected");
    stopCountdownTimer();
    scheduleReconnect();
  };

  socket.onerror = (error) => {
    console.error("WebSocket error:", error);
    updateStatus("disconnected");
    stopCountdownTimer();
  };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  stopCountdownTimer();
  reconnectTimer = setTimeout(() => {
    console.log("Reconnecting WebSocket...");
    connectWebSocket();
  }, 3000);
}

// Atualizar indicador de conexão
function updateStatus(state) {
  currentConnectionState = state;
  if (!statusPill || !statusText || !statusIndicator) return;

  statusPill.className = "flex items-center gap-2 px-2.5 py-1 rounded-md text-xs font-mono transition-colors border";

  if (state === "connected") {
    statusPill.className += " bg-[#13161c] border-emerald-500/20 text-emerald-400";
    statusIndicator.innerHTML = `
      <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
    `;
    statusText.textContent = t("status_connected");
  } else if (state === "connecting") {
    statusPill.className += " bg-[#13161c] border-amber-500/20 text-amber-300";
    statusIndicator.innerHTML = `
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
      <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-400"></span>
    `;
    statusText.textContent = t("status_connecting");
  } else {
    statusPill.className += " bg-[#13161c] border-rose-500/20 text-rose-400";
    statusIndicator.innerHTML = `
      <span class="relative inline-flex rounded-full h-2 w-2 bg-rose-400"></span>
    `;
    statusText.textContent = t("status_disconnected");
  }
}

// Renderização principal do dashboard
function renderDashboard(data) {
  if (!data) return;

  // 0. Server Name (Aba do navegador, cabeçalho e metadados PWA)
  if (data.server_name) {
    const serverNameEl = document.getElementById("server-name-display");
    if (serverNameEl && serverNameEl.textContent !== data.server_name) {
      serverNameEl.textContent = data.server_name;
    }
    if (document.title !== data.server_name) {
      document.title = data.server_name;
    }
    const metaApple = document.getElementById("meta-apple-title");
    if (metaApple) metaApple.content = data.server_name;
    const metaApp = document.getElementById("meta-app-name");
    if (metaApp) metaApp.content = data.server_name;
  }


  // Update simple timestamp (no label)
  const now = new Date();
  if (lastUpdate) {
    lastUpdate.textContent = now.toLocaleTimeString("en-GB", { hour12: false });
  }

  // 1. Uptime (sanitizes any prefix to avoid duplication with HTML label)
  if (uptimeDisplay) {
    if (data.uptime && data.uptime.uptime_formatted) {
      let cleanUptime = String(data.uptime.uptime_formatted)
        .replace(/^uptime:\s*/i, "")
        .replace(/^tempo de atividade:\s*/i, "")
        .trim();
      
      // Traduz sufixos d/h/m se em português (ex: "1d 2h 30m" para "1d 2h 30m" - d/h/m é padrão em ambos os idiomas)
      uptimeDisplay.textContent = cleanUptime;
    } else {
      uptimeDisplay.textContent = "--";
    }
  }

  // 2. CPU Total e Load Average
  const cpuEl = document.getElementById("cpu-total");
  const cpuBar = document.getElementById("cpu-bar");
  const cpuCoresCount = document.getElementById("cpu-core-count");
  const cpuLoad = document.getElementById("cpu-load");

  if (data.cpu && data.cpu.total_percent !== undefined && data.cpu.total_percent !== null) {
    const cpuVal = Number(data.cpu.total_percent);
    const cpuColors = getStatusColor(cpuVal);

    if (cpuEl) {
      cpuEl.textContent = `${cpuVal.toFixed(1)}%`;
      cpuEl.className = `text-3xl font-semibold tracking-tight font-mono ${cpuColors.text}`;
    }
    if (cpuBar) {
      cpuBar.style.width = `${Math.min(100, Math.max(0, cpuVal))}%`;
      cpuBar.className = `h-1.5 rounded-full transition-all duration-500 ${cpuColors.bar}`;
    }
    if (cpuCoresCount) {
      cpuCoresCount.textContent = `${data.cpu.core_count ?? 0} vCPUs`;
    }
    renderCpuCores(data.cpu.per_core_percent || []);
  } else {
    if (cpuEl) {
      cpuEl.textContent = "--";
      cpuEl.className = "text-3xl font-semibold tracking-tight font-mono text-slate-500";
    }
    if (cpuBar) cpuBar.style.width = "0%";
    if (cpuCoresCount) cpuCoresCount.textContent = "--";
    renderCpuCores([]);
  }

  // Load average: apenas os números separados por vírgula
  if (data.load_average && data.load_average.last_1m !== undefined) {
    if (cpuLoad) {
      const l1 = Number(data.load_average.last_1m).toFixed(2);
      const l5 = Number(data.load_average.last_5m).toFixed(2);
      const l15 = Number(data.load_average.last_15m).toFixed(2);
      cpuLoad.textContent = `${l1}, ${l5}, ${l15}`;
    }
  } else if (cpuLoad) {
    cpuLoad.textContent = "- / - / -";
  }

  // 3. Memory & Swap (apenas números e frações)
  const ramPercent = document.getElementById("ram-percent");
  const ramRatio = document.getElementById("ram-ratio");
  const ramBar = document.getElementById("ram-bar");
  const swapInfo = document.getElementById("swap-info");

  if (data.virtual_memory && data.virtual_memory.percent !== undefined && data.virtual_memory.percent !== null) {
    const ram = data.virtual_memory;
    const ramColors = getStatusColor(ram.percent);

    if (ramPercent) {
      ramPercent.textContent = `${ram.percent.toFixed(1)}%`;
      ramPercent.className = `text-3xl font-semibold tracking-tight font-mono ${ramColors.text}`;
    }
    if (ramRatio) {
      ramRatio.textContent = `${ram.used_gb.toFixed(1)} / ${ram.total_gb.toFixed(1)} GB`;
    }
    if (ramBar) {
      ramBar.style.width = `${Math.min(100, Math.max(0, ram.percent))}%`;
      ramBar.className = `h-1.5 rounded-full transition-all duration-500 ${ramColors.bar}`;
    }
  } else {
    if (ramPercent) {
      ramPercent.textContent = "--";
      ramPercent.className = "text-3xl font-semibold tracking-tight font-mono text-slate-500";
    }
    if (ramRatio) ramRatio.textContent = "0 / 0 GB";
    if (ramBar) ramBar.style.width = "0%";
  }

  if (swapInfo) {
    if (data.swap_memory && data.swap_memory.total_gb > 0) {
      swapInfo.textContent = `${data.swap_memory.used_gb.toFixed(1)} / ${data.swap_memory.total_gb.toFixed(1)} GB (${data.swap_memory.percent.toFixed(0)}%)`;
    } else if (data.swap_memory && data.swap_memory.total_gb === 0) {
      swapInfo.textContent = t("disabled");
    } else {
      swapInfo.textContent = `--`;
    }
  }

  // 4. Disk (apenas números e frações)
  const diskPercent = document.getElementById("disk-percent");
  const diskRatio = document.getElementById("disk-ratio");
  const diskFree = document.getElementById("disk-free");
  const diskBar = document.getElementById("disk-bar");

  if (data.root_storage && data.root_storage.percent !== undefined && data.root_storage.percent !== null) {
    const disk = data.root_storage;
    const diskColors = getStatusColor(disk.percent);

    if (diskPercent) {
      diskPercent.textContent = `${disk.percent.toFixed(1)}%`;
      diskPercent.className = `text-3xl font-semibold tracking-tight font-mono ${diskColors.text}`;
    }
    if (diskRatio) {
      diskRatio.textContent = `${disk.used_gb.toFixed(1)} / ${disk.total_gb.toFixed(1)} GB`;
    }
    if (diskFree) {
      diskFree.textContent = `${disk.free_gb.toFixed(1)} GB`;
    }
    if (diskBar) {
      diskBar.style.width = `${Math.min(100, Math.max(0, disk.percent))}%`;
      diskBar.className = `h-1.5 rounded-full transition-all duration-500 ${diskColors.bar}`;
    }
  } else {
    if (diskPercent) {
      diskPercent.textContent = "--";
      diskPercent.className = "text-3xl font-semibold tracking-tight font-mono text-slate-500";
    }
    if (diskRatio) diskRatio.textContent = "0 / 0 GB";
    if (diskFree) diskFree.textContent = "--";
    if (diskBar) diskBar.style.width = "0%";
  }

  // 5. Docker
  const dockerBadge = document.getElementById("docker-status-badge");
  const dockerSubtext = document.getElementById("docker-subtext");
  const runningCount = document.getElementById("docker-running-count");
  const stoppedCount = document.getElementById("docker-stopped-count");
  const totalBadge = document.getElementById("containers-total-badge");

  if (data.docker) {
    const d = data.docker;
    if (dockerBadge) {
      if (d.is_running) {
        dockerBadge.textContent = t("active");
        dockerBadge.className = "px-2 py-0.5 rounded text-[11px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      } else {
        dockerBadge.textContent = t("inactive");
        dockerBadge.className = "px-2 py-0.5 rounded text-[11px] font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20";
      }
    }

    const total = d.summary?.total ?? (d.containers ? d.containers.length : 0);
    const running = d.summary?.running ?? (d.containers ? d.containers.filter(c => c.state === "running").length : 0);
    const stopped = d.summary?.stopped ?? (total - running);

    if (runningCount) runningCount.textContent = running;
    if (stoppedCount) stoppedCount.textContent = stopped;
    if (totalBadge) totalBadge.textContent = t("total_badge", total);
    if (dockerSubtext) dockerSubtext.textContent = t("containers_count", total);

    renderContainersTable(d.containers || [], d.is_running);
  } else {
    if (dockerBadge) {
      dockerBadge.textContent = "n/a";
      dockerBadge.className = "px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-400 border border-slate-700";
    }
    if (runningCount) runningCount.textContent = "0";
    if (stoppedCount) stoppedCount.textContent = "0";
    if (totalBadge) totalBadge.textContent = t("total_badge", 0);
    if (dockerSubtext) dockerSubtext.textContent = t("containers_count", 0);
    renderContainersTable([], false);
  }

  // 6. Network & Disk I/O
  renderNetworkInterfaces(data.network_interfaces || []);

  const readMb = document.getElementById("disk-read-mb");
  const writeMb = document.getElementById("disk-write-mb");
  if (data.disk_io) {
    if (readMb) readMb.textContent = `${data.disk_io.read_mb.toFixed(1)} MB`;
    if (writeMb) writeMb.textContent = `${data.disk_io.write_mb.toFixed(1)} MB`;
  } else {
    if (readMb) readMb.textContent = "0.0 MB";
    if (writeMb) writeMb.textContent = "0.0 MB";
  }

  // 7. Active sessions (apenas o número)
  const usersCount = document.getElementById("users-count");
  if (usersCount) {
    const count = (data.logged_in_users || []).length;
    usersCount.textContent = String(count);
  }

  // 8. Top Processes
  renderProcessTable("cpu-processes-body", data.top_cpu_processes || [], "cpu");
  renderProcessTable("memory-processes-body", data.top_memory_processes || [], "memory");
}

// Renderizar medidores por core
function renderCpuCores(cores) {
  const container = document.getElementById("cores-grid");
  if (!container) return;

  if (!cores || cores.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 col-span-full py-6 text-center font-mono">${escapeHtml(t("no_cores"))}</div>`;
    return;
  }

  container.innerHTML = cores.map((usage, idx) => {
    const val = (usage !== null && usage !== undefined && !isNaN(usage)) ? Number(usage) : null;
    const colors = getStatusColor(val);
    const displayVal = val !== null ? `${val.toFixed(1)}%` : "--";
    const widthVal = val !== null ? Math.min(100, Math.max(0, val)) : 0;

    const coreLabel = currentLang === "pt" ? `núcleo ${idx}` : `core ${idx}`;
    return `
      <div class="bg-[#171b23] p-3 rounded-lg border border-[#202530] flex flex-col justify-between font-mono">
        <div class="flex items-center justify-between text-xs mb-2">
          <span class="text-slate-400">${coreLabel}</span>
          <span class="${colors.text}">${displayVal}</span>
        </div>
        <div class="w-full bg-[#1e222a] rounded-full h-1 overflow-hidden">
          <div class="h-1 rounded-full ${colors.bar} transition-all duration-300" style="width: ${widthVal}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

// Renderizar interfaces de rede
function renderNetworkInterfaces(interfaces) {
  const container = document.getElementById("network-interfaces-list");
  if (!container) return;

  if (!interfaces || interfaces.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 py-2 text-center">${escapeHtml(t("no_interfaces"))}</div>`;
    return;
  }

  container.innerHTML = interfaces.map(iface => `
    <div class="flex items-center justify-between p-2 rounded bg-[#171b23] border border-[#202530] text-xs font-mono">
      <span class="text-slate-200 font-medium">${escapeHtml(iface.interface)}</span>
      <div class="flex items-center gap-3 text-[11px]">
        <span class="text-slate-300">↓ ${(iface.bytes_recv_mb ?? 0).toFixed(1)} MB</span>
        <span class="text-slate-400">↑ ${(iface.bytes_sent_mb ?? 0).toFixed(1)} MB</span>
      </div>
    </div>
  `).join("");
}

// Renderizar tabela de containers Docker
function renderContainersTable(containers, isDaemonRunning) {
  const tbody = document.getElementById("containers-table-body");
  if (!tbody) return;

  if (!isDaemonRunning) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-6 text-center text-slate-500 font-mono">${escapeHtml(t("docker_unreachable"))}</td>
      </tr>
    `;
    return;
  }

  if (!containers || containers.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-6 text-center text-slate-500 font-mono">${escapeHtml(t("no_running_containers"))}</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = containers.map(c => {
    const isRunning = c.state === "running";
    const statusPillClass = isRunning
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
      : "bg-slate-800 text-slate-400 border-slate-700";

    const portsStr = c.ports && Object.keys(c.ports).length > 0
      ? Object.keys(c.ports).slice(0, 3).join(", ")
      : "-";

    return `
      <tr class="hover:bg-[#161a22] transition-colors border-b border-[#1e222a]">
        <td class="py-2.5 px-3 font-medium text-white">${escapeHtml(c.name)}</td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded text-[11px] font-mono border ${statusPillClass}">${escapeHtml(formatContainerStatus(c.status, c.state))}</span>
        </td>
        <td class="py-2.5 px-3 text-slate-300 truncate max-w-[220px]" title="${escapeHtml(c.image)}">${escapeHtml(c.image)}</td>
        <td class="py-2.5 px-3 text-slate-400 font-mono text-[11px]">${escapeHtml(c.id ? c.id.slice(0, 12) : '-')}</td>
        <td class="py-2.5 px-3 text-slate-400 font-mono text-[11px]">${escapeHtml(portsStr)}</td>
      </tr>
    `;
  }).join("");
}

// Renderizar tabelas de processos
function renderProcessTable(elementId, processes, highlightKey) {
  const tbody = document.getElementById(elementId);
  if (!tbody) return;

  if (!processes || processes.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="py-6 text-center text-slate-500 font-mono">${escapeHtml(t("no_processes"))}</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = processes.slice(0, 10).map(proc => {
    const isCpuHighlight = highlightKey === "cpu";
    const cpuClass = isCpuHighlight ? "text-emerald-400 font-medium" : "text-slate-400";
    const memClass = !isCpuHighlight ? "text-blue-400 font-medium" : "text-slate-400";

    const cpuVal = proc.cpu_percent !== undefined ? proc.cpu_percent.toFixed(1) : "0.0";
    const memVal = proc.memory_percent !== undefined ? proc.memory_percent.toFixed(1) : "0.0";

    return `
      <tr class="hover:bg-[#161a22] transition-colors border-b border-[#1e222a]">
        <td class="py-2 px-3 text-slate-500 font-mono text-[11px]">${proc.pid}</td>
        <td class="py-2 px-3 text-slate-200 truncate max-w-[160px] font-mono" title="${escapeHtml(proc.name)}">${escapeHtml(proc.name)}</td>
        <td class="py-2 px-3 text-right font-mono text-xs ${cpuClass}">${cpuVal}%</td>
        <td class="py-2 px-3 text-right font-mono text-xs ${memClass}">${memVal}%</td>
      </tr>
    `;
  }).join("");
}

// Utilitário de escape HTML básico contra XSS
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Inicialização
document.addEventListener("DOMContentLoaded", () => {
  // Bind nos botões de idioma
  const btnEn = document.getElementById("lang-btn-en");
  const btnPt = document.getElementById("lang-btn-pt");

  if (btnEn) {
    btnEn.addEventListener("click", () => setLanguage("en"));
  }
  if (btnPt) {
    btnPt.addEventListener("click", () => setLanguage("pt"));
  }

  // Configura estado inicial do idioma
  updateLanguageUI();

  // Conecta WebSocket
  connectWebSocket();

  // Registra Service Worker para PWA
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker
        .register("sw.js", { scope: "./" })
        .then((reg) => {
          console.log("Service Worker registered with scope:", reg.scope);
        })
        .catch((err) => {
          console.warn("Service Worker registration failed:", err);
        });
    });
  }
});

