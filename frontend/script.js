
// Detecta host e porta automaticamente do navegador ou usa localhost:8000 como fallback
const hostWithPort = (typeof window !== "undefined" && window.location.host && window.location.host !== "")
  ? window.location.host
  : "localhost:8000";
const protocol = (typeof window !== "undefined" && window.location.protocol === "https:") ? "wss:" : "ws:";
const WS_URL = `${protocol}//${hostWithPort}/ws/data`;
let socket = null;
let reconnectTimer = null;

// Elementos da UI
const statusPill = document.getElementById("status-pill");
const statusIndicator = document.getElementById("status-indicator");
const statusText = document.getElementById("status-text");
const lastUpdate = document.getElementById("last-update");
const uptimeDisplay = document.getElementById("uptime-display");

// Helper: Cores baseadas em porcentagem
function getStatusColor(percent) {
  if (percent >= 85) return { bar: "bg-red-500", text: "text-red-400" };
  if (percent >= 70) return { bar: "bg-amber-500", text: "text-amber-400" };
  return { bar: "bg-emerald-500", text: "text-emerald-400" };
}

// Conectar ao WebSocket
function connectWebSocket() {
  clearTimeout(reconnectTimer);
  updateStatus("connecting");

  try {
    socket = new WebSocket(WS_URL);
  } catch (err) {
    console.error("Erro ao inicializar WebSocket:", err);
    scheduleReconnect();
    return;
  }

  socket.onopen = () => {
    updateStatus("connected");
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      renderDashboard(data);
    } catch (err) {
      console.error("Erro ao parsear dados JSON:", err);
    }
  };

  socket.onclose = () => {
    updateStatus("disconnected");
    scheduleReconnect();
  };

  socket.onerror = (error) => {
    console.error("WebSocket erro:", error);
    updateStatus("error");
  };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    console.log("Tentando reconectar WebSocket...");
    connectWebSocket();
  }, 3000);
}

// Atualizar indicador de conexão
function updateStatus(state) {
  if (!statusPill || !statusText || !statusIndicator) return;

  statusPill.className = "flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium transition-colors";

  if (state === "connected") {
    statusPill.classList.add("border-emerald-500/30", "bg-emerald-500/10", "text-emerald-400");
    statusIndicator.innerHTML = `
      <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
    `;
    statusText.textContent = "Conectado";
  } else if (state === "connecting") {
    statusPill.classList.add("border-amber-500/30", "bg-amber-500/10", "text-amber-400");
    statusIndicator.innerHTML = `
      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
      <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
    `;
    statusText.textContent = "Conectando...";
  } else {
    statusPill.classList.add("border-rose-500/30", "bg-rose-500/10", "text-rose-400");
    statusIndicator.innerHTML = `
      <span class="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
    `;
    statusText.textContent = "Desconectado";
  }
}

// Renderização principal do dashboard
function renderDashboard(data) {
  if (!data) return;

  // Atualizar carimbo de data/hora
  const now = new Date();
  if (lastUpdate) {
    lastUpdate.textContent = now.toLocaleTimeString("pt-BR");
  }

  // 1. Uptime
  if (data.uptime && uptimeDisplay) {
    uptimeDisplay.innerHTML = `Uptime: <span class="text-slate-300 font-mono font-semibold">${data.uptime.uptime_formatted}</span>`;
  }

  // 2. CPU Total e Load Average
  if (data.cpu) {
    const cpuVal = data.cpu.total_percent ?? 0;
    const cpuColors = getStatusColor(cpuVal);

    const cpuEl = document.getElementById("cpu-total");
    const cpuBar = document.getElementById("cpu-bar");
    const cpuCoresCount = document.getElementById("cpu-core-count");

    if (cpuEl) {
      cpuEl.textContent = `${cpuVal.toFixed(1)}%`;
      cpuEl.className = `text-3xl font-extrabold font-mono ${cpuColors.text}`;
    }
    if (cpuBar) {
      cpuBar.style.width = `${Math.min(cpuVal, 100)}%`;
      cpuBar.className = `h-2 rounded-full transition-all duration-500 ${cpuColors.bar}`;
    }
    if (cpuCoresCount) {
      cpuCoresCount.textContent = `${data.cpu.core_count} vCPUs`;
    }

    // Cores Individuais
    renderCpuCores(data.cpu.per_core_percent || []);
  }

  if (data.load_average) {
    const cpuLoad = document.getElementById("cpu-load");
    if (cpuLoad) {
      cpuLoad.textContent = `Load: ${data.load_average.last_1m.toFixed(2)} / ${data.load_average.last_5m.toFixed(2)} / ${data.load_average.last_15m.toFixed(2)}`;
    }
  }

  // 3. Memória RAM & Swap
  if (data.virtual_memory) {
    const ram = data.virtual_memory;
    const ramColors = getStatusColor(ram.percent);

    const ramPercent = document.getElementById("ram-percent");
    const ramRatio = document.getElementById("ram-ratio");
    const ramBar = document.getElementById("ram-bar");

    if (ramPercent) {
      ramPercent.textContent = `${ram.percent.toFixed(1)}%`;
      ramPercent.className = `text-3xl font-extrabold font-mono ${ramColors.text}`;
    }
    if (ramRatio) {
      ramRatio.textContent = `${ram.used_gb.toFixed(1)} / ${ram.total_gb.toFixed(1)} GB`;
    }
    if (ramBar) {
      ramBar.style.width = `${Math.min(ram.percent, 100)}%`;
      ramBar.className = `h-2 rounded-full transition-all duration-500 ${ramColors.bar}`;
    }
  }

  if (data.swap_memory) {
    const swapInfo = document.getElementById("swap-info");
    if (swapInfo) {
      swapInfo.textContent = `Swap: ${data.swap_memory.percent.toFixed(0)}% (${data.swap_memory.used_gb.toFixed(1)} GB)`;
    }
  }

  // 4. Disco Root
  if (data.root_storage) {
    const disk = data.root_storage;
    const diskColors = getStatusColor(disk.percent);

    const diskPercent = document.getElementById("disk-percent");
    const diskRatio = document.getElementById("disk-ratio");
    const diskFree = document.getElementById("disk-free");
    const diskBar = document.getElementById("disk-bar");

    if (diskPercent) {
      diskPercent.textContent = `${disk.percent.toFixed(1)}%`;
      diskPercent.className = `text-3xl font-extrabold font-mono ${diskColors.text}`;
    }
    if (diskRatio) {
      diskRatio.textContent = `${disk.used_gb.toFixed(1)} / ${disk.total_gb.toFixed(1)} GB`;
    }
    if (diskFree) {
      diskFree.textContent = `Livre: ${disk.free_gb.toFixed(1)} GB`;
    }
    if (diskBar) {
      diskBar.style.width = `${Math.min(disk.percent, 100)}%`;
      diskBar.className = `h-2 rounded-full transition-all duration-500 ${diskColors.bar}`;
    }
  }

  // 5. Docker Overview
  if (data.docker) {
    const d = data.docker;
    const badge = document.getElementById("docker-status-badge");
    const runningCount = document.getElementById("docker-running-count");
    const stoppedCount = document.getElementById("docker-stopped-count");
    const totalBadge = document.getElementById("containers-total-badge");

    if (badge) {
      if (d.is_running) {
        badge.textContent = "Ativo";
        badge.className = "text-xs px-2 py-0.5 rounded font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
      } else {
        badge.textContent = "Inativo / Indisponível";
        badge.className = "text-xs px-2 py-0.5 rounded font-mono bg-rose-500/10 text-rose-400 border border-rose-500/20";
      }
    }

    if (runningCount) runningCount.textContent = d.summary?.running ?? 0;
    if (stoppedCount) stoppedCount.textContent = d.summary?.stopped ?? 0;
    if (totalBadge) totalBadge.textContent = d.summary?.total ?? 0;

    renderContainersTable(d.containers || []);
  }

  // 6. I/O e Rede
  renderNetworkInterfaces(data.network_interfaces || []);

  if (data.disk_io) {
    const readMb = document.getElementById("disk-read-mb");
    const writeMb = document.getElementById("disk-write-mb");
    if (readMb) readMb.textContent = `${data.disk_io.read_mb.toFixed(1)} MB`;
    if (writeMb) writeMb.textContent = `${data.disk_io.write_mb.toFixed(1)} MB`;
  }

  // 7. Usuários logados
  const usersCount = document.getElementById("users-count");
  if (usersCount) {
    const count = (data.logged_in_users || []).length;
    usersCount.textContent = `${count} sessão(ões)`;
  }

  // 8. Processos Top CPU e RAM
  renderProcessTable("cpu-processes-body", data.top_cpu_processes || [], "cpu");
  renderProcessTable("memory-processes-body", data.top_memory_processes || [], "memory");
}

// Renderizar medidores de cada núcleo de CPU
function renderCpuCores(cores) {
  const container = document.getElementById("cores-grid");
  if (!container) return;

  if (cores.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 col-span-full py-2">Sem métricas por núcleo disponíveis</div>`;
    return;
  }

  container.innerHTML = cores.map((usage, idx) => {
    const colors = getStatusColor(usage);
    return `
      <div class="bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
        <div class="flex items-center justify-between text-xs mb-1.5">
          <span class="text-slate-400 font-mono">CPU ${idx}</span>
          <span class="font-mono font-bold ${colors.text}">${usage.toFixed(1)}%</span>
        </div>
        <div class="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div class="h-1.5 rounded-full ${colors.bar} transition-all duration-300" style="width: ${Math.min(usage, 100)}%"></div>
        </div>
      </div>
    `;
  }).join("");
}

// Renderizar interfaces de rede
function renderNetworkInterfaces(interfaces) {
  const container = document.getElementById("network-interfaces-list");
  if (!container) return;

  if (interfaces.length === 0) {
    container.innerHTML = `<div class="text-xs text-slate-500 py-1">Nenhuma interface de rede detectada.</div>`;
    return;
  }

  container.innerHTML = interfaces.map(iface => `
    <div class="flex items-center justify-between p-2 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
      <span class="font-mono font-semibold text-slate-300">${escapeHtml(iface.interface)}</span>
      <div class="flex items-center gap-3 font-mono text-[11px]">
        <span class="text-emerald-400">↓ ${iface.bytes_recv_mb.toFixed(1)} MB</span>
        <span class="text-blue-400">↑ ${iface.bytes_sent_mb.toFixed(1)} MB</span>
      </div>
    </div>
  `).join("");
}

// Renderizar tabela de containers Docker
function renderContainersTable(containers) {
  const tbody = document.getElementById("containers-table-body");
  if (!tbody) return;

  if (containers.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" class="py-4 text-center text-slate-500 font-sans">Nenhum container Docker ativo no momento.</td>
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
      <tr class="hover:bg-slate-800/40 transition-colors">
        <td class="py-2.5 px-3 font-semibold text-white">${escapeHtml(c.name)}</td>
        <td class="py-2.5 px-3">
          <span class="px-2 py-0.5 rounded-full border text-[11px] ${statusPillClass}">${escapeHtml(c.status || c.state)}</span>
        </td>
        <td class="py-2.5 px-3 text-slate-400 truncate max-w-[200px]" title="${escapeHtml(c.image)}">${escapeHtml(c.image)}</td>
        <td class="py-2.5 px-3 text-slate-500">${escapeHtml(c.id)}</td>
        <td class="py-2.5 px-3 text-slate-400">${escapeHtml(portsStr)}</td>
      </tr>
    `;
  }).join("");
}

// Renderizar tabelas de processos (CPU ou Memória)
function renderProcessTable(elementId, processes, highlightKey) {
  const tbody = document.getElementById(elementId);
  if (!tbody) return;

  if (processes.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="py-3 text-center text-slate-500 font-sans">Nenhum processo listado.</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = processes.slice(0, 10).map(proc => {
    const isCpuHighlight = highlightKey === "cpu";
    const cpuClass = isCpuHighlight ? "text-emerald-400 font-bold" : "text-slate-400";
    const memClass = !isCpuHighlight ? "text-blue-400 font-bold" : "text-slate-400";

    return `
      <tr class="hover:bg-slate-800/40 transition-colors">
        <td class="py-2 px-3 text-slate-500">${proc.pid}</td>
        <td class="py-2 px-3 text-slate-200 font-sans truncate max-w-[140px]" title="${escapeHtml(proc.name)}">${escapeHtml(proc.name)}</td>
        <td class="py-2 px-3 text-right ${cpuClass}">${proc.cpu_percent.toFixed(1)}%</td>
        <td class="py-2 px-3 text-right ${memClass}">${proc.memory_percent.toFixed(1)}%</td>
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
  connectWebSocket();
});
