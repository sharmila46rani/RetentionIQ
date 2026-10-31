/**
 * RetentionIQ Main Client Script
 */

document.addEventListener("DOMContentLoaded", function () {
  // Client-side quick filter on data tables
  const searchInputs = document.querySelectorAll(".table-search-input");
  searchInputs.forEach(input => {
    input.addEventListener("keyup", function () {
      const targetTableId = this.getAttribute("data-target");
      const targetTable = document.getElementById(targetTableId);
      if (!targetTable) return;

      const query = this.value.toLowerCase().trim();
      const rows = targetTable.querySelectorAll("tbody tr");

      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? "" : "none";
      });
    });
  });
});

// Chart.js helper functions
window.RetentionCharts = {
  colors: {
    navy: "#0F172A",
    teal: "#0D9488",
    tealLight: "#14B8A6",
    tealSubtle: "#CCFBF1",
    danger: "#EF4444",
    warning: "#F59E0B",
    success: "#10B981",
    gray: "#94A3B8",
    blue: "#3B82F6",
  },

  createLineChart: function (canvasId, labels, data, datasetLabel) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    return new Chart(ctx, {
      type: "line",
      data: {
        labels: labels,
        datasets: [{
          label: datasetLabel,
          data: data,
          borderColor: this.colors.teal,
          backgroundColor: "rgba(13, 148, 136, 0.1)",
          fill: true,
          tension: 0.3,
          pointRadius: 4,
          pointBackgroundColor: this.colors.teal,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { grid: { color: "#F1F5F9" } },
          x: { grid: { display: false } }
        }
      }
    });
  },

  createDoughnutChart: function (canvasId, labels, data, backgroundColors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    return new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: backgroundColors || [this.colors.success, this.colors.warning, this.colors.danger, this.colors.teal],
          borderWidth: 2,
          borderColor: "#FFFFFF",
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom" }
        },
        cutout: "70%"
      }
    });
  },

  createBarChart: function (canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    return new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: datasets
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "top" }
        },
        scales: {
          y: { grid: { color: "#F1F5F9" } },
          x: { grid: { display: false } }
        }
      }
    });
  }
};
