// Real-time Dashboard Controller: Vision AI, Safety Compliance & Weather Monitoring
document.addEventListener('DOMContentLoaded', () => {
    
    // ================= DOM Elements =================
    const clockDisplay = document.getElementById('clockDisplay');
    const kpiCompliance = document.getElementById('kpiCompliance');
    const kpiComplianceSub = document.getElementById('kpiComplianceSub');
    const kpiWorkers = document.getElementById('kpiWorkers');
    const kpiCompliantWorkers = document.getElementById('kpiCompliantWorkers');
    const kpiViolations = document.getElementById('kpiViolations');
    const kpiViolationDetails = document.getElementById('kpiViolationDetails');
    const kpiHazardStatus = document.getElementById('kpiHazardStatus');
    const hazardBanner = document.getElementById('hazardBanner');
    const incidentsContainer = document.getElementById('incidentsContainer');
    const activeSourceLabel = document.getElementById('activeSourceLabel');
    const currentZoneBadge = document.getElementById('currentZoneBadge');

    // Weather Elements
    const weatherAlertBanner = document.getElementById('weatherAlertBanner');
    const weatherAlertIcon = document.getElementById('weatherAlertIcon');
    const weatherAlertHeadline = document.getElementById('weatherAlertHeadline');
    const weatherAlertRiskTag = document.getElementById('weatherAlertRiskTag');
    const weatherAlertMetrics = document.getElementById('weatherAlertMetrics');
    const weatherAlertExplanation = document.getElementById('weatherAlertExplanation');
    const btnDismissWeatherAlert = document.getElementById('btnDismissWeatherAlert');

    const weatherOfflineBanner = document.getElementById('weatherOfflineBanner');
    const offlineLastUpdated = document.getElementById('offlineLastUpdated');
    const btnRetryWeather = document.getElementById('btnRetryWeather');

    const demoBanner = document.getElementById('demoBanner');
    const btnDemoToggle = document.getElementById('btnDemoToggle');
    const demoStatusText = document.getElementById('demoStatusText');
    const btnDemoHeatSpike = document.getElementById('btnDemoHeatSpike');
    const btnDemoNormal = document.getElementById('btnDemoNormal');
    const btnDisableDemo = document.getElementById('btnDisableDemo');

    const weatherLocationName = document.getElementById('weatherLocationName');
    const weatherDataSourceTag = document.getElementById('weatherDataSourceTag');
    const weatherLastUpdatedText = document.getElementById('weatherLastUpdatedText');
    const btnRefreshWeatherNow = document.getElementById('btnRefreshWeatherNow');
    const refreshSpinner = document.getElementById('refreshSpinner');

    const valTemperature = document.getElementById('valTemperature');
    const badgeTempStatus = document.getElementById('badgeTempStatus');
    const trendIndicator = document.getElementById('trendIndicator');

    const valHumidity = document.getElementById('valHumidity');
    const badgeHumidityStatus = document.getElementById('badgeHumidityStatus');
    const valWindPressure = document.getElementById('valWindPressure');

    const valHeatIndex = document.getElementById('valHeatIndex');
    const formulaText = document.getElementById('formulaText');

    const valRiskBadge = document.getElementById('valRiskBadge');
    const valRiskCondition = document.getElementById('valRiskCondition');
    const reasonsListContainer = document.getElementById('reasonsListContainer');
    const conclusionContainer = document.getElementById('conclusionContainer');

    // Controls
    const btnAudioTest = document.getElementById('btnAudioTest');
    const btnMuteToggle = document.getElementById('btnMuteToggle');
    const muteStatusText = document.getElementById('muteStatusText');
    const btnCameraSettings = document.getElementById('btnCameraSettings');
    const btnRefreshFeed = document.getElementById('btnRefreshFeed');
    const btnFullscreen = document.getElementById('btnFullscreen');
    const videoWrapper = document.getElementById('videoWrapper');
    const liveVideoFeed = document.getElementById('liveVideoFeed');

    // Modals
    const cameraModal = document.getElementById('cameraModal');
    const btnCloseModal = document.getElementById('btnCloseModal');
    const btnCancelModal = document.getElementById('btnCancelModal');
    const cameraConfigForm = document.getElementById('cameraConfigForm');
    const sourceSelect = document.getElementById('sourceSelect');
    const modalUrlInput = document.getElementById('modalUrlInput');
    const zoneInput = document.getElementById('zoneInput');

    const snapshotModal = document.getElementById('snapshotModal');
    const btnCloseSnapshot = document.getElementById('btnCloseSnapshot');
    const snapshotZoomImg = document.getElementById('snapshotZoomImg');
    const snapshotModalDetails = document.getElementById('snapshotModalDetails');

    const quickSourceForm = document.getElementById('quickSourceForm');
    const quickSourceInput = document.getElementById('quickSourceInput');

    let isMuted = false;
    let isDemoMode = false;
    let weatherChart = null;

    // ================= 1. Clock Display =================
    function updateClock() {
        const now = new Date();
        clockDisplay.innerText = now.toTimeString().split(' ')[0];
    }
    setInterval(updateClock, 1000);
    updateClock();

    // ================= 2. Live Video & Vision Stats =================
    async function fetchStats() {
        try {
            const res = await fetch('/api/stats');
            if (!res.ok) return;
            const data = await res.json();
            
            const live = data.live || {};
            
            // Compliance Rate
            kpiCompliance.innerText = `${live.compliance_rate ?? 100}%`;
            if (live.compliance_rate >= 80) {
                kpiCompliance.style.color = 'var(--safe)';
                kpiComplianceSub.innerText = 'Safe Compliance Level';
            } else if (live.compliance_rate >= 50) {
                kpiCompliance.style.color = 'var(--warning)';
                kpiComplianceSub.innerText = 'Moderate Violation Risk';
            } else {
                kpiCompliance.style.color = 'var(--danger)';
                kpiComplianceSub.innerText = 'Critical Violation Level';
            }

            // Workers
            kpiWorkers.innerText = live.total_workers ?? 0;
            kpiCompliantWorkers.innerText = live.compliant_workers ?? 0;

            // Violations
            kpiViolations.innerText = live.violations_count ?? 0;
            if (live.active_violations && live.active_violations.length > 0) {
                kpiViolationDetails.innerText = live.active_violations.join(', ');
            } else {
                kpiViolationDetails.innerText = 'No active violations';
            }

            // Multi-Hazard Status Flags
            const tagFall = document.getElementById('tagFall');
            const tagGeofence = document.getElementById('tagGeofence');
            const tagHeight = document.getElementById('tagHeight');
            const tagDropZone = document.getElementById('tagDropZone');
            const tagConfined = document.getElementById('tagConfined');
            const tagHotWork = document.getElementById('tagHotWork');
            const tagTrench = document.getElementById('tagTrench');
            const tagProximity = document.getElementById('tagProximity');
            const tagNight = document.getElementById('tagNight');
            const kpiHazardDetails = document.getElementById('kpiHazardDetails');
            const hazardTitle = document.getElementById('hazardTitle');
            const hazardDesc = document.getElementById('hazardDesc');
            const hazardIcon = document.getElementById('hazardIcon');

            if (tagFall) {
                tagFall.innerText = live.fall_detected ? '🚨 Fall: EMERGENCY DOWN' : '🚶 Fall: Normal';
                tagFall.className = live.fall_detected ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagGeofence) {
                tagGeofence.innerText = live.danger_breached ? '🛑 Geofence: BREACHED' : '🛑 Geofence: Secure';
                tagGeofence.className = live.danger_breached ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagHeight) {
                tagHeight.innerText = live.height_violation ? '⚠️ Height: NO HARNESS' : '🏗️ Height: Secure';
                tagHeight.className = live.height_violation ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagDropZone) {
                tagDropZone.innerText = live.suspended_load_hazard ? '🚨 Drop Zone: LINE OF FIRE' : '📦 Drop Zone: Clear';
                tagDropZone.className = live.suspended_load_hazard ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagConfined) {
                const count = live.confined_headcount ?? 0;
                tagConfined.innerText = live.confined_overstay ? '🚨 Confined: OVERSTAY' : `🚪 Confined: ${count} Safe`;
                tagConfined.className = live.confined_overstay ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagHotWork) {
                tagHotWork.innerText = live.hot_work_violation ? '⚠️ Hot Work: NO EXTINGUISHER' : (live.hot_work_active ? '⚡ Hot Work: Active [OK]' : '⚡ Hot Work: Clear');
                tagHotWork.className = live.hot_work_violation ? 'tele-tag active-alert' : (live.hot_work_active ? 'tele-tag active-working' : 'tele-tag');
            }
            if (tagTrench) {
                tagTrench.innerText = live.trench_hazard ? '🚨 Trench: CAVE-IN RISK' : '⚠️ Trench: Setback Safe';
                tagTrench.className = live.trench_hazard ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagProximity) {
                tagProximity.innerText = live.proximity_alert ? '🚜 Proximity: COLLISION WARN' : '🚜 Proximity: Clear';
                tagProximity.className = live.proximity_alert ? 'tele-tag active-alert' : 'tele-tag';
            }
            if (tagNight) {
                tagNight.innerText = live.night_intrusion ? '🚨 Night: INTRUDER DETECTED' : (live.night_mode ? '🌙 Night Guard: ACTIVE' : '🌙 Night Guard: Off');
                tagNight.className = live.night_intrusion ? 'tele-tag active-alert' : (live.night_mode ? 'tele-tag active-working' : 'tele-tag');
            }

            // Emergency Banner & Status Badge
            if (live.fire_detected) {
                kpiHazardStatus.innerText = '🔥 FIRE DETECTED!';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Open flame / smoke signature active';
                if (hazardTitle) hazardTitle.innerText = 'CRITICAL: FIRE HAZARD DETECTED';
                if (hazardDesc) hazardDesc.innerText = 'Open flame signature detected. Evacuation siren active.';
                if (hazardIcon) hazardIcon.innerText = '🔥';
                hazardBanner.style.display = 'flex';
            } else if (live.fall_detected) {
                kpiHazardStatus.innerText = '🚨 WORKER DOWN!';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Horizontal posture collapse detected';
                if (hazardTitle) hazardTitle.innerText = 'EMERGENCY: WORKER FALL DETECTED';
                if (hazardDesc) hazardDesc.innerText = 'Worker fallen or unresponsive. Medical team alerted.';
                if (hazardIcon) hazardIcon.innerText = '🚨';
                hazardBanner.style.display = 'flex';
            } else if (live.suspended_load_hazard) {
                kpiHazardStatus.innerText = '🚨 LINE OF FIRE!';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Worker underneath crane suspended load drop zone';
                if (hazardTitle) hazardTitle.innerText = 'CRANE DROP ZONE HAZARD';
                if (hazardDesc) hazardDesc.innerText = 'Personnel detected in suspended load drop shadow!';
                if (hazardIcon) hazardIcon.innerText = '📦';
                hazardBanner.style.display = 'flex';
            } else if (live.height_violation) {
                kpiHazardStatus.innerText = '⚠️ HARNESS VIOLATION';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Unharnessed worker in elevated zone';
                hazardBanner.style.display = 'none';
            } else if (live.hot_work_violation) {
                kpiHazardStatus.innerText = '⚠️ HOT WORK HAZARD';
                kpiHazardStatus.className = 'kpi-badge badge-warning';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Welding active without fire extinguisher nearby';
                hazardBanner.style.display = 'none';
            } else if (live.confined_overstay) {
                kpiHazardStatus.innerText = '🚨 CONFINED OVERSTAY';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Worker exceeded maximum safe duration limit';
                hazardBanner.style.display = 'none';
            } else if (live.trench_hazard) {
                kpiHazardStatus.innerText = '⚠️ TRENCH MARGIN RISK';
                kpiHazardStatus.className = 'kpi-badge badge-warning';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Worker or equipment violating excavation setback';
                hazardBanner.style.display = 'none';
            } else if (live.danger_breached) {
                kpiHazardStatus.innerText = '🛑 PERIMETER BREACH';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Worker in restricted machine perimeter';
                hazardBanner.style.display = 'none';
            } else if (live.night_intrusion) {
                kpiHazardStatus.innerText = '🚨 NIGHT INTRUDER';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Unauthorized movement during night security lockdown';
                hazardBanner.style.display = 'none';
            } else if (live.phone_detected || live.proximity_alert) {
                kpiHazardStatus.innerText = '⚠️ BEHAVIOR HAZARD';
                kpiHazardStatus.className = 'kpi-badge badge-warning';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'Active proximity / distraction warning';
                hazardBanner.style.display = 'none';
            } else {
                kpiHazardStatus.innerText = 'SAFE';
                kpiHazardStatus.className = 'kpi-badge badge-safe';
                if (kpiHazardDetails) kpiHazardDetails.innerText = 'All modules clear';
                hazardBanner.style.display = 'none';
            }

            // Auto-Pilot & Master Controls UI Synchronization
            if (data.feature_matrix) {
                syncMasterControlsFromMatrix(data.feature_matrix);
            }

            // Gate Mode UI Synchronization
            const gateBadge = document.getElementById('liveModeBadge');
            const gateBtnText = document.getElementById('gateModeText');
            const btnGateModeToggle = document.getElementById('btnGateModeToggle');
            if (data.gate_mode) {
                if (gateBadge) gateBadge.style.display = 'inline-block';
                if (gateBtnText) gateBtnText.innerText = 'GATE: ACTIVE';
                if (btnGateModeToggle) btnGateModeToggle.classList.add('active');
            } else {
                if (gateBadge) gateBadge.style.display = 'none';
                if (gateBtnText) gateBtnText.innerText = 'GATE: OFF';
                if (btnGateModeToggle) btnGateModeToggle.classList.remove('active');
            }

            // Update Source & Zone
            activeSourceLabel.innerText = `Source: ${data.camera_source}`;
            currentZoneBadge.innerText = `📍 ${data.zone_name}`;
            isMuted = data.is_muted;
            muteStatusText.innerText = isMuted ? 'MUTED' : 'ON';

            // Sensitivity sync
            if (data.sensitivity && typeof renderSensitivityUI === 'function') {
                const isSliding = (typeof sliderConfidence !== 'undefined' && document.activeElement === sliderConfidence) ||
                                  (typeof sliderCooldown !== 'undefined' && document.activeElement === sliderCooldown);
                if (!isSliding) {
                    renderSensitivityUI(data.sensitivity.level, data.sensitivity.conf_thresh, data.sensitivity.cooldown);
                }
            }

        } catch (e) {
            console.error('Stats poll error:', e);
        }
    }
    setInterval(fetchStats, 1000);
    fetchStats();

    // ================= 3. Incident History & Snapshots =================
    async function fetchIncidents() {
        try {
            const res = await fetch('/api/incidents');
            if (!res.ok) return;
            const data = await res.json();
            const incidents = data.incidents || [];

            if (incidents.length === 0) {
                incidentsContainer.innerHTML = '<div class="empty-state">No violations recorded yet. System is monitoring.</div>';
                return;
            }

            incidentsContainer.innerHTML = incidents.map(inc => {
                const isCritical = inc.severity === 'CRITICAL' || inc.incident_type.includes('Fire') || inc.incident_type.includes('Thermal');
                const tagClass = isCritical ? 'tag-critical' : 'tag-high';
                const thumb = inc.snapshot_path ? inc.snapshot_path : '/static/incidents/placeholder.jpg';

                return `
                    <div class="incident-card">
                        <img src="${thumb}" alt="Snapshot" class="incident-thumb" onclick="openSnapshotModal('${thumb}', '${inc.incident_type} - ${inc.timestamp}', '${inc.details}')" onerror="this.src='data:image/svg+xml;utf8,<svg xmlns=\\'http://www.w3.org/2000/svg\\' width=\\'65\\' height=\\'48\\' fill=\\'%23334155\\'><rect width=\\'65\\' height=\\'48\\'/></svg>'">
                        <div class="incident-info">
                            <div class="incident-title">
                                <span class="tag-violation ${tagClass}">${inc.severity}</span>
                                <span>${inc.incident_type}</span>
                            </div>
                            <div class="incident-meta">
                                <span>🕒 ${inc.timestamp}</span>
                                <span>📍 ${inc.zone}</span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (e) {
            console.error('Incidents poll error:', e);
        }
    }
    setInterval(fetchIncidents, 3000);
    fetchIncidents();

    // ================= 4. Weather Monitoring & Anomaly Logic =================
    async function updateWeatherUI(w) {
        if (!w) return;

        // Offline state handling
        if (w.is_offline) {
            weatherOfflineBanner.style.display = 'flex';
            offlineLastUpdated.innerText = w.last_updated ? `(Last Sync: ${w.last_updated})` : '(No previous data)';
        } else {
            weatherOfflineBanner.style.display = 'none';
        }

        // Demo Mode Banner
        isDemoMode = !!w.is_demo;
        if (isDemoMode) {
            demoBanner.style.display = 'flex';
            demoStatusText.innerText = 'DEMO: ON';
            btnDemoToggle.classList.add('btn-accent');
        } else {
            demoBanner.style.display = 'none';
            demoStatusText.innerText = 'DEMO: OFF';
            btnDemoToggle.classList.remove('btn-accent');
        }

        // Location & Source Meta
        weatherLocationName.innerText = `📍 ${w.location || 'Bhubaneswar, Odisha, India'}`;
        weatherDataSourceTag.innerText = w.data_source || 'Real-Time Weather API';
        weatherLastUpdatedText.innerText = w.last_updated || '--';

        // 1. Temperature Card
        if (w.temperature !== null && w.temperature !== undefined) {
            valTemperature.innerText = w.temperature.toFixed(1);
            badgeTempStatus.innerText = w.temp_status || 'Normal';
            trendIndicator.innerText = `${w.trend_icon || '→'} ${w.trend || 'Steady'}`;

            // Temperature status pill color
            if (w.temperature >= 40.0) {
                badgeTempStatus.className = 'status-pill status-danger';
            } else if (w.temperature >= 35.0) {
                badgeTempStatus.className = 'status-pill status-warning';
            } else if (w.temperature >= 28.0) {
                badgeTempStatus.className = 'status-pill status-info';
            } else {
                badgeTempStatus.className = 'status-pill status-normal';
            }
        }

        // 2. Relative Humidity Card
        if (w.humidity !== null && w.humidity !== undefined) {
            valHumidity.innerText = Math.round(w.humidity);
            badgeHumidityStatus.innerText = w.humidity_status || 'Comfortable';
            valWindPressure.innerText = `💨 ${w.wind_speed || 0} km/h | ${w.pressure || 1013} hPa`;

            if (w.humidity >= 75.0) {
                badgeHumidityStatus.className = 'status-pill status-danger';
            } else if (w.humidity >= 60.0) {
                badgeHumidityStatus.className = 'status-pill status-warning';
            } else {
                badgeHumidityStatus.className = 'status-pill status-info';
            }
        }

        // 3. Heat Index Card
        if (w.heat_index !== null && w.heat_index !== undefined) {
            valHeatIndex.innerText = w.heat_index.toFixed(1);
            formulaText.innerText = w.heat_index_formula || `${w.temperature}°C + ${w.humidity}% → ${w.heat_index}°C`;
        }

        // 4. Occupational Risk Level Card
        const rLevel = (w.risk_level || 'LOW').toUpperCase();
        valRiskBadge.innerText = w.risk_badge || `🟢 ${rLevel}`;
        valRiskCondition.innerText = `${w.condition || 'Clear'} | Atmospheric State`;

        // Update Risk badge styling
        valRiskBadge.className = 'risk-badge-display';
        if (rLevel === 'CRITICAL') {
            valRiskBadge.classList.add('risk-critical');
        } else if (rLevel === 'HIGH') {
            valRiskBadge.classList.add('risk-high');
        } else if (rLevel === 'MODERATE') {
            valRiskBadge.classList.add('risk-moderate');
        } else {
            valRiskBadge.classList.add('risk-low');
        }

        // 5. Explainable Anomaly Reasons
        if (w.reasons && w.reasons.length > 0) {
            reasonsListContainer.innerHTML = w.reasons.map(r => `<li>${r}</li>`).join('');
        } else {
            reasonsListContainer.innerHTML = '<li>Atmospheric conditions are within standard safety thresholds.</li>';
        }
        conclusionContainer.innerText = w.conclusion || 'Environmental safety state normal.';

        // 6. Visual Alert Banner (for HIGH or CRITICAL heat hazard or anomaly)
        if (rLevel === 'CRITICAL' || rLevel === 'HIGH' || w.is_anomaly) {
            weatherAlertBanner.style.display = 'flex';
            weatherAlertHeadline.innerText = rLevel === 'CRITICAL' ? 'CRITICAL THERMAL HAZARD DETECTED' : 'ELEVATED HEAT STRESS ADVISORY';
            weatherAlertRiskTag.innerText = rLevel;
            weatherAlertIcon.innerText = rLevel === 'CRITICAL' ? '🔴' : '🟠';
            weatherAlertMetrics.innerHTML = `Temperature: <strong>${w.temperature}°C</strong> | Humidity: <strong>${w.humidity}%</strong> | Calculated Heat Index: <strong>${w.heat_index}°C</strong>`;
            
            const firstReason = (w.reasons && w.reasons.length > 0) ? w.reasons[0] : 'Heat index has crossed occupational threshold.';
            weatherAlertExplanation.innerHTML = `<strong>Why detected:</strong> ${firstReason}`;
        } else {
            weatherAlertBanner.style.display = 'none';
        }
    }

    async function fetchCurrentWeather(force = false) {
        try {
            refreshSpinner.classList.add('spinning');
            const endpoint = force ? '/api/weather/refresh' : '/api/weather/current';
            const method = force ? 'POST' : 'GET';
            const res = await fetch(endpoint, { method: method });
            if (!res.ok) return;
            const data = await res.json();
            updateWeatherUI(data);
            await fetchWeatherHistory();
        } catch (e) {
            console.error('Weather fetch error:', e);
            weatherOfflineBanner.style.display = 'flex';
        } finally {
            setTimeout(() => {
                refreshSpinner.classList.remove('spinning');
            }, 600);
        }
    }

    // Refresh Now Button
    btnRefreshWeatherNow.addEventListener('click', () => {
        fetchCurrentWeather(true);
    });

    btnRetryWeather.addEventListener('click', () => {
        fetchCurrentWeather(true);
    });

    btnDismissWeatherAlert.addEventListener('click', () => {
        weatherAlertBanner.style.display = 'none';
    });

    // Auto-poll weather every 30s for fast synchronization
    setInterval(() => fetchCurrentWeather(false), 30000);
    fetchCurrentWeather(true);

    // ================= 5. Chart.js Multi-Metric Historical Graph =================
    function initWeatherChart(labels, tempData, humidityData, heatIndexData) {
        const ctx = document.getElementById('weatherHistoryChart');
        if (!ctx) return;

        if (weatherChart) {
            weatherChart.destroy();
        }

        weatherChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Temperature (°C)',
                        data: tempData,
                        borderColor: '#F97316',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        borderWidth: 2.5,
                        tension: 0.35,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#F97316',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Humidity (%)',
                        data: humidityData,
                        borderColor: '#06B6D4',
                        backgroundColor: 'rgba(6, 182, 212, 0.08)',
                        borderWidth: 2,
                        tension: 0.35,
                        pointRadius: 3,
                        pointHoverRadius: 5,
                        pointBackgroundColor: '#06B6D4',
                        yAxisID: 'y1'
                    },
                    {
                        label: 'Heat Index (°C)',
                        data: heatIndexData,
                        borderColor: '#EF4444',
                        backgroundColor: 'rgba(239, 68, 68, 0.15)',
                        borderWidth: 2.5,
                        borderDash: [5, 4],
                        tension: 0.35,
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#EF4444',
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        display: false // Using our custom aesthetic header legend
                    },
                    tooltip: {
                        backgroundColor: '#1E293B',
                        titleColor: '#F9FAFB',
                        bodyColor: '#E2E8F0',
                        borderColor: '#334155',
                        borderWidth: 1,
                        padding: 10,
                        boxPadding: 4,
                        usePointStyle: true,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y + (context.datasetIndex === 1 ? '%' : '°C');
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(51, 65, 85, 0.3)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#94A3B8',
                            font: { family: "'JetBrains Mono', monospace", size: 10 },
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Temp & Heat Index (°C)',
                            color: '#F97316',
                            font: { size: 11, weight: 'bold' }
                        },
                        grid: {
                            color: 'rgba(51, 65, 85, 0.3)',
                            drawBorder: false
                        },
                        ticks: {
                            color: '#CBD5E1',
                            font: { family: "'JetBrains Mono', monospace", size: 10 }
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Humidity (%)',
                            color: '#06B6D4',
                            font: { size: 11, weight: 'bold' }
                        },
                        grid: {
                            drawOnChartArea: false // Avoid overlapping grid lines
                        },
                        ticks: {
                            color: '#06B6D4',
                            font: { family: "'JetBrains Mono', monospace", size: 10 }
                        }
                    }
                }
            }
        });
    }

    async function fetchWeatherHistory() {
        try {
            const res = await fetch('/api/weather/history?limit=25');
            if (!res.ok) return;
            const data = await res.json();
            const history = data.history || [];

            if (history.length === 0) return;

            const labels = history.map(item => item.timestamp);
            const tempData = history.map(item => item.temperature);
            const humidityData = history.map(item => item.humidity);
            const heatIndexData = history.map(item => item.heat_index);

            if (!weatherChart) {
                initWeatherChart(labels, tempData, humidityData, heatIndexData);
            } else {
                weatherChart.data.labels = labels;
                weatherChart.data.datasets[0].data = tempData;
                weatherChart.data.datasets[1].data = humidityData;
                weatherChart.data.datasets[2].data = heatIndexData;
                weatherChart.update('none'); // Silent smooth update
            }
        } catch (e) {
            console.error('History fetch error:', e);
        }
    }

    // ================= 6. Demo / Simulation Mode Controls =================
    async function setDemoMode(enabled, temp = null, humidity = null) {
        const formData = new FormData();
        formData.append('enabled', enabled ? 'true' : 'false');
        if (temp !== null) formData.append('temp', temp.toString());
        if (humidity !== null) formData.append('humidity', humidity.toString());

        try {
            const res = await fetch('/api/weather/demo-mode', { method: 'POST', body: formData });
            if (!res.ok) return;
            const data = await res.json();
            updateWeatherUI(data.weather);
            await fetchWeatherHistory();
        } catch (e) {
            console.error('Demo toggle error:', e);
        }
    }

    btnDemoToggle.addEventListener('click', () => {
        isDemoMode = !isDemoMode;
        setDemoMode(isDemoMode, isDemoMode ? 42.0 : null, isDemoMode ? 75.0 : null);
    });

    btnDemoHeatSpike.addEventListener('click', () => {
        setDemoMode(true, 43.5, 78.0);
    });

    btnDemoNormal.addEventListener('click', () => {
        setDemoMode(true, 29.0, 52.0);
    });

    btnDisableDemo.addEventListener('click', () => {
        setDemoMode(false);
    });

    // ================= 7. Audio Controls =================
    btnAudioTest.addEventListener('click', async () => {
        btnAudioTest.innerText = '🔊 Testing...';
        const formData = new FormData();
        formData.append('trigger_test', 'true');
        await fetch('/api/alarm/toggle', { method: 'POST', body: formData });
        setTimeout(() => {
            btnAudioTest.innerText = '🔊 Test Speaker';
        }, 2000);
    });

    btnMuteToggle.addEventListener('click', async () => {
        isMuted = !isMuted;
        const formData = new FormData();
        formData.append('mute', isMuted ? 'true' : 'false');
        await fetch('/api/alarm/toggle', { method: 'POST', body: formData });
        muteStatusText.innerText = isMuted ? 'MUTED' : 'ON';
    });

    // ================= 8. Video Feed Watchdog =================
    function reloadFeed() {
        liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
    }

    btnRefreshFeed.addEventListener('click', reloadFeed);

    liveVideoFeed.onerror = () => {
        console.warn('[Stream] Video feed disconnected, auto-reconnecting in 2s...');
        setTimeout(reloadFeed, 2000);
    };

    btnFullscreen.addEventListener('click', () => {
        if (!document.fullscreenElement) {
            videoWrapper.requestFullscreen().catch(err => alert(`Fullscreen error: ${err.message}`));
        } else {
            document.exitFullscreen();
        }
    });

    // ================= 9. Fast Camera Switch =================
    quickSourceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const sourceVal = quickSourceInput.value.trim();
        if (!sourceVal) return;

        const formData = new FormData();
        formData.append('source', sourceVal);
        formData.append('zone', currentZoneBadge.innerText.replace('📍 ', ''));

        await fetch('/api/settings', { method: 'POST', body: formData });
        liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
    });

    const mediaUploadInput = document.getElementById('mediaUploadInput');
    const btnUploadMedia = document.getElementById('btnUploadMedia');
    const btnTestFirePreset = document.getElementById('btnTestFirePreset');
    const btnTestLighterPreset = document.getElementById('btnTestLighterPreset');
    const btnWebcamPreset = document.getElementById('btnWebcamPreset');

    if (btnUploadMedia && mediaUploadInput) {
        btnUploadMedia.addEventListener('click', () => mediaUploadInput.click());
        mediaUploadInput.addEventListener('change', async () => {
            if (!mediaUploadInput.files || mediaUploadInput.files.length === 0) return;
            const file = mediaUploadInput.files[0];
            const originalText = btnUploadMedia.innerText;
            btnUploadMedia.innerText = '⏳ Uploading...';
            try {
                const formData = new FormData();
                formData.append('file', file);
                formData.append('zone', 'Upload Inspection Feed');
                const res = await fetch('/api/upload-media', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.status === 'success') {
                    quickSourceInput.value = data.source_path;
                    liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
                    btnUploadMedia.innerText = '✅ Inspecting!';
                    setTimeout(() => { btnUploadMedia.innerText = originalText; }, 2000);
                } else {
                    alert('Upload failed: ' + (data.message || 'Unknown error'));
                    btnUploadMedia.innerText = originalText;
                }
            } catch (err) {
                console.error('Upload error:', err);
                btnUploadMedia.innerText = originalText;
            }
        });
    }

    if (btnTestFirePreset) {
        btnTestFirePreset.addEventListener('click', async () => {
            const formData = new FormData();
            formData.append('source', 'static/images/test/fire_pillar.png');
            formData.append('zone', 'Fire Testing Area');
            await fetch('/api/settings', { method: 'POST', body: formData });
            quickSourceInput.value = 'static/images/test/fire_pillar.png';
            liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
        });
    }

    if (btnTestLighterPreset) {
        btnTestLighterPreset.addEventListener('click', async () => {
            const formData = new FormData();
            formData.append('source', 'static/images/test/lighter_flame.png');
            formData.append('zone', 'Combustion Jet Zone');
            await fetch('/api/settings', { method: 'POST', body: formData });
            quickSourceInput.value = 'static/images/test/lighter_flame.png';
            liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
        });
    }

    if (btnWebcamPreset) {
        btnWebcamPreset.addEventListener('click', async () => {
            const formData = new FormData();
            formData.append('source', '0');
            formData.append('zone', 'Zone 1 - Main Floor');
            await fetch('/api/settings', { method: 'POST', body: formData });
            quickSourceInput.value = '0';
            liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
        });
    }

    // ================= 10. Modals Management =================
    btnCameraSettings.addEventListener('click', () => {
        cameraModal.style.display = 'flex';
    });

    btnCloseModal.addEventListener('click', () => {
        cameraModal.style.display = 'none';
    });

    btnCancelModal.addEventListener('click', () => {
        cameraModal.style.display = 'none';
    });

    const urlInputLabel = document.getElementById('urlInputLabel');
    const cameraHelperText = document.getElementById('cameraHelperText');

    sourceSelect.addEventListener('change', () => {
        const val = sourceSelect.value;
        if (val === 'droidcam-wifi') {
            if (urlInputLabel) urlInputLabel.innerText = 'DroidCam Wi-Fi Stream URL:';
            modalUrlInput.value = 'http://192.168.1.15:4747/video';
            modalUrlInput.placeholder = 'http://192.168.1.15:4747/video';
            if (cameraHelperText) cameraHelperText.innerHTML = '💡 <b>DroidCam Wi-Fi:</b> Open DroidCam on phone, connect to same Wi-Fi/Hotspot, and enter the IP shown on phone (e.g. <code>http://192.168.1.15:4747/video</code>).';
        } else if (val === 'droidcam-usb') {
            if (urlInputLabel) urlInputLabel.innerText = 'USB Camera Index:';
            modalUrlInput.value = '1';
            modalUrlInput.placeholder = '1 (or 2)';
            if (cameraHelperText) cameraHelperText.innerHTML = '⚡ <b>Zero Lag USB Mode:</b> Connect phone via USB with DroidCam/Iriun Windows client running. Use Index <code>1</code> (or <code>2</code>).';
        } else if (val === 'webcam') {
            if (urlInputLabel) urlInputLabel.innerText = 'Laptop Webcam Index:';
            modalUrlInput.value = '0';
            modalUrlInput.placeholder = '0';
            if (cameraHelperText) cameraHelperText.innerHTML = '💻 <b>Laptop Webcam:</b> Default built-in webcam index is <code>0</code>.';
        } else if (val === 'ipwebcam') {
            if (urlInputLabel) urlInputLabel.innerText = 'IP Webcam Stream URL:';
            modalUrlInput.value = 'http://192.168.1.15:8080/video';
            modalUrlInput.placeholder = 'http://192.168.1.15:8080/video';
            if (cameraHelperText) cameraHelperText.innerHTML = '📱 <b>IP Webcam:</b> Open IP Webcam app, tap <i>Start Server</i> at bottom, enter the URL with <code>/video</code>.';
        } else if (val === 'custom') {
            if (urlInputLabel) urlInputLabel.innerText = 'RTSP / Stream URL or File:';
            modalUrlInput.value = 'rtsp://192.168.1.15:554/live';
            modalUrlInput.placeholder = 'rtsp://... or path/to/video.mp4';
            if (cameraHelperText) cameraHelperText.innerHTML = '🌐 <b>Custom Source:</b> Enter an RTSP URL, HTTP stream URL, or local video file path.';
        }
    });

    cameraConfigForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const sourceVal = modalUrlInput.value.trim();
        const zoneVal = zoneInput.value.trim();

        const formData = new FormData();
        formData.append('source', sourceVal);
        formData.append('zone', zoneVal);

        await fetch('/api/settings', { method: 'POST', body: formData });
        cameraModal.style.display = 'none';
        quickSourceInput.value = sourceVal;
        liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;
    });

    // Snapshot Modal
    window.openSnapshotModal = function(imgSrc, title, details) {
        snapshotZoomImg.src = imgSrc;
        document.getElementById('snapshotModalTitle').innerText = title;
        snapshotModalDetails.innerText = details || 'Violation evidence image saved by AI vision detector.';
        snapshotModal.style.display = 'flex';
    };

    btnCloseSnapshot.addEventListener('click', () => {
        snapshotModal.style.display = 'none';
    });

    // ================= 11. Smart Gate Mode Controller handled via Master Feature Switchboard =================

    // ================= 12. AI Safety Copilot Drawer & Chat =================
    const copilotModal = document.getElementById('copilotModal');
    const btnOpenCopilot = document.getElementById('btnOpenCopilot');
    const btnCloseCopilot = document.getElementById('btnCloseCopilot');
    const copilotForm = document.getElementById('copilotForm');
    const copilotInput = document.getElementById('copilotInput');
    const copilotChatBody = document.getElementById('copilotChatBody');
    const chipBtns = document.querySelectorAll('.chip-btn');

    if (btnOpenCopilot) {
        btnOpenCopilot.addEventListener('click', () => {
            copilotModal.style.display = 'flex';
            copilotInput.focus();
        });
    }

    if (btnCloseCopilot) {
        btnCloseCopilot.addEventListener('click', () => {
            copilotModal.style.display = 'none';
        });
    }

    function appendCopilotMessage(sender, text, mode) {
        const msgDiv = document.createElement('div');
        msgDiv.className = sender === 'user' ? 'chat-msg user-msg' : 'chat-msg ai-msg';
        
        const avatar = document.createElement('div');
        avatar.className = 'msg-avatar';
        avatar.innerText = sender === 'user' ? '👤' : '🤖';

        const content = document.createElement('div');
        content.className = 'msg-content';

        // Parse simple markdown headers and bullets
        let formatted = text
            .replace(/### (.*?)\n/g, '<h3>$1</h3>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/• (.*?)\n/g, '<li>$1</li>')
            .replace(/\n\n/g, '<br><br>');

        if (mode) {
            formatted += `<br><small style="opacity: 0.6; font-size: 0.72rem;">Engine: ${mode}</small>`;
        }

        content.innerHTML = formatted;
        msgDiv.appendChild(avatar);
        msgDiv.appendChild(content);
        copilotChatBody.appendChild(msgDiv);
        copilotChatBody.scrollTop = copilotChatBody.scrollHeight;
    }

    async function sendCopilotQuery(query) {
        if (!query || !query.trim()) return;
        const q = query.trim();
        appendCopilotMessage('user', q);
        copilotInput.value = '';

        // Add thinking placeholder
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'chat-msg ai-msg';
        thinkingDiv.id = 'copilotThinking';
        thinkingDiv.innerHTML = '<div class="msg-avatar">🤖</div><div class="msg-content"><em>Analyzing factory telemetry & OSHA guidelines...</em></div>';
        copilotChatBody.appendChild(thinkingDiv);
        copilotChatBody.scrollTop = copilotChatBody.scrollHeight;

        try {
            const formData = new FormData();
            formData.append('query', q);
            const res = await fetch('/api/copilot/chat', { method: 'POST', body: formData });
            const data = await res.json();
            
            const thinking = document.getElementById('copilotThinking');
            if (thinking) thinking.remove();

            appendCopilotMessage('ai', data.response, data.mode);
        } catch (e) {
            const thinking = document.getElementById('copilotThinking');
            if (thinking) thinking.remove();
            appendCopilotMessage('ai', 'Error connecting to Safety Copilot engine. Please retry.');
        }
    }

    if (copilotForm) {
        copilotForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendCopilotQuery(copilotInput.value);
        });
    }

    chipBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const q = btn.getAttribute('data-query');
            sendCopilotQuery(q);
        });
    });

    // ================= 13. Safety Scorecard & 2D Spatial Heatmap =================
    const scorecardModal = document.getElementById('scorecardModal');
    const btnOpenScorecard = document.getElementById('btnOpenScorecard');
    const btnCloseScorecard = document.getElementById('btnCloseScorecard');
    const heatmapCanvas = document.getElementById('heatmapCanvas');

    if (btnOpenScorecard) {
        btnOpenScorecard.addEventListener('click', async () => {
            scorecardModal.style.display = 'flex';
            await loadScorecardData();
            await renderSpatialHeatmap();
        });
    }

    if (btnCloseScorecard) {
        btnCloseScorecard.addEventListener('click', () => {
            scorecardModal.style.display = 'none';
        });
    }

    async function loadScorecardData() {
        try {
            const res = await fetch('/api/analytics/scorecard');
            const data = await res.json();
            
            const scGradeBadge = document.getElementById('scGradeBadge');
            const scGradeDesc = document.getElementById('scGradeDesc');
            const scScoreNumber = document.getElementById('scScoreNumber');
            const scStreakDays = document.getElementById('scStreakDays');
            const scOshaRate = document.getElementById('scOshaRate');

            if (scGradeBadge) {
                scGradeBadge.innerText = data.grade;
                scGradeBadge.style.color = data.grade_color;
            }
            if (scGradeDesc) scGradeDesc.innerText = data.grade_desc;
            if (scScoreNumber) scScoreNumber.innerText = data.score;
            if (scStreakDays) scStreakDays.innerText = data.zero_accident_days;
            if (scOshaRate) scOshaRate.innerText = `${data.osha_compliance_pct}%`;
        } catch (e) {
            console.error('Scorecard fetch error:', e);
        }
    }

    async function renderSpatialHeatmap() {
        if (!heatmapCanvas) return;
        const ctx = heatmapCanvas.getContext('2d');
        const cw = heatmapCanvas.width;
        const ch = heatmapCanvas.height;

        // Clear canvas
        ctx.fillStyle = '#050A18';
        ctx.fillRect(0, 0, cw, ch);

        // Draw Floor Plan Grid
        ctx.strokeStyle = '#152033';
        ctx.lineWidth = 1;
        for (let x = 0; x < cw; x += 40) {
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, ch);
            ctx.stroke();
        }
        for (let y = 0; y < ch; y += 40) {
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(cw, y);
            ctx.stroke();
        }

        // Draw Zone Boundaries
        ctx.strokeStyle = '#223656';
        ctx.setLineDash([4, 4]);
        ctx.strokeRect(20, 20, cw * 0.45, ch - 40);
        ctx.strokeRect(cw * 0.52, 20, cw * 0.45, ch - 40);
        ctx.setLineDash([]);

        ctx.fillStyle = '#64748B';
        ctx.font = '11px sans-serif';
        ctx.fillText('ZONE 1: ASSEMBLY & ROBOTICS', 30, 40);
        ctx.fillText('ZONE 2: FORKLIFT & LOADING BAY', cw * 0.55, 40);

        try {
            const res = await fetch('/api/analytics/heatmap');
            const data = await res.json();
            const points = data.points || [];

            // Plot incident points
            points.forEach(pt => {
                const px = (pt.coord_x || 0.5) * cw;
                const py = (pt.coord_y || 0.5) * ch;
                const cat = (pt.category || 'PPE').toUpperCase();

                let color = 'rgba(245, 158, 11, 0.7)'; // PPE yellow
                if (cat.includes('FALL')) color = 'rgba(239, 68, 68, 0.9)'; // Red
                else if (cat.includes('PERIMETER')) color = 'rgba(139, 92, 246, 0.8)'; // Purple
                else if (cat.includes('FIRE')) color = 'rgba(249, 115, 22, 0.9)'; // Orange
                else if (cat.includes('DISTRACTION')) color = 'rgba(236, 72, 153, 0.8)'; // Pink

                // Radial Glow
                const grad = ctx.createRadialGradient(px, py, 2, px, py, 14);
                grad.addColorStop(0, color);
                grad.addColorStop(1, 'rgba(0,0,0,0)');

                ctx.fillStyle = grad;
                ctx.beginPath();
                ctx.arc(px, py, 14, 0, Math.PI * 2);
                ctx.fill();

                // Center Point
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(px, py, 3, 0, Math.PI * 2);
                ctx.fill();
            });

        } catch (e) {
            console.error('Heatmap render error:', e);
        }
    }

    // ================= 14. Danger Zone Geofence Modal =================
    const dangerZoneModal = document.getElementById('dangerZoneModal');
    const btnDangerZoneModal = document.getElementById('btnDangerZoneModal');
    const btnCloseDangerZone = document.getElementById('btnCloseDangerZone');
    const btnCancelDangerZone = document.getElementById('btnCancelDangerZone');
    const dangerZoneForm = document.getElementById('dangerZoneForm');
    const chkDangerEnable = document.getElementById('chkDangerEnable');
    const dangerZoneNameInput = document.getElementById('dangerZoneNameInput');
    const dangerPresetSelect = document.getElementById('dangerPresetSelect');

    const presets = {
        right: [[0.60, 0.25], [0.96, 0.25], [0.96, 0.85], [0.60, 0.85]],
        left: [[0.05, 0.25], [0.45, 0.25], [0.45, 0.85], [0.05, 0.85]],
        bottom: [[0.10, 0.65], [0.90, 0.65], [0.90, 0.95], [0.10, 0.95]],
        center: [[0.30, 0.30], [0.70, 0.30], [0.70, 0.75], [0.30, 0.75]]
    };

    if (btnDangerZoneModal) {
        btnDangerZoneModal.addEventListener('click', () => {
            dangerZoneModal.style.display = 'flex';
        });
    }

    if (btnCloseDangerZone) btnCloseDangerZone.addEventListener('click', () => dangerZoneModal.style.display = 'none');
    if (btnCancelDangerZone) btnCancelDangerZone.addEventListener('click', () => dangerZoneModal.style.display = 'none');

    if (dangerZoneForm) {
        dangerZoneForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const enabled = chkDangerEnable.checked;
            const name = dangerZoneNameInput.value.trim() || 'Heavy Machinery Perimeter';
            const presetKey = dangerPresetSelect.value || 'right';
            const poly = presets[presetKey] || presets.right;

            const formData = new FormData();
            formData.append('enabled', enabled ? 'true' : 'false');
            formData.append('name', name);
            formData.append('poly_json', JSON.stringify(poly));

            await fetch('/api/danger-zone', { method: 'POST', body: formData });
            dangerZoneModal.style.display = 'none';
        });
    }

    // ================= 15. Telegram Mobile Alert Modal =================
    const telegramModal = document.getElementById('telegramModal');
    const btnTelegramModal = document.getElementById('btnTelegramModal');
    const btnCloseTelegram = document.getElementById('btnCloseTelegram');
    const btnCancelTelegram = document.getElementById('btnCancelTelegram');
    const telegramForm = document.getElementById('telegramForm');
    const chkTelegramEnable = document.getElementById('chkTelegramEnable');
    const tgBotTokenInput = document.getElementById('tgBotTokenInput');
    const tgChatIdInput = document.getElementById('tgChatIdInput');
    const btnTestTelegram = document.getElementById('btnTestTelegram');
    const tgTestStatus = document.getElementById('tgTestStatus');

    if (btnTelegramModal) {
        btnTelegramModal.addEventListener('click', async () => {
            telegramModal.style.display = 'flex';
            try {
                const res = await fetch('/api/telegram/config');
                const data = await res.json();
                if (data.token) tgBotTokenInput.value = data.token;
                if (data.chat_id) tgChatIdInput.value = data.chat_id;
                chkTelegramEnable.checked = data.enabled !== false;
            } catch (e) {
                console.warn('Failed to load telegram config:', e);
            }
        });
    }

    if (btnCloseTelegram) btnCloseTelegram.addEventListener('click', () => telegramModal.style.display = 'none');
    if (btnCancelTelegram) btnCancelTelegram.addEventListener('click', () => telegramModal.style.display = 'none');

    if (telegramForm) {
        telegramForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const token = tgBotTokenInput.value.trim();
            const chat_id = tgChatIdInput.value.trim();
            const enabled = chkTelegramEnable.checked;

            const formData = new FormData();
            formData.append('token', token);
            formData.append('chat_id', chat_id);
            formData.append('enabled', enabled ? 'true' : 'false');

            await fetch('/api/telegram/config', { method: 'POST', body: formData });
            tgTestStatus.innerText = '✅ Configuration saved!';
            tgTestStatus.style.color = '#10B981';
            setTimeout(() => {
                telegramModal.style.display = 'none';
                tgTestStatus.innerText = '';
            }, 800);
        });
    }

    if (btnTestTelegram) {
        btnTestTelegram.addEventListener('click', async () => {
            const token = tgBotTokenInput.value.trim();
            const chat_id = tgChatIdInput.value.trim();

            if (!token || !chat_id) {
                tgTestStatus.innerText = '⚠️ Please enter both Bot Token and Chat ID above!';
                tgTestStatus.style.color = '#F59E0B';
                return;
            }

            tgTestStatus.innerText = '⏳ Sending test alert to your Telegram...';
            tgTestStatus.style.color = '#38BDF8';

            try {
                const formData = new FormData();
                formData.append('token', token);
                formData.append('chat_id', chat_id);
                formData.append('enabled', 'true');

                const res = await fetch('/api/telegram/test', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.status === 'success') {
                    tgTestStatus.innerText = '✅ Test alert delivered to your phone!';
                    tgTestStatus.style.color = '#10B981';
                } else {
                    tgTestStatus.innerText = `⚠️ ${data.message || 'Check Token & Chat ID'}`;
                    tgTestStatus.style.color = '#F59E0B';
                }
            } catch (e) {
                tgTestStatus.innerText = '❌ Error triggering alert.';
                tgTestStatus.style.color = '#EF4444';
            }
        });
    }

    const btnSimulateTelegram = document.getElementById('btnSimulateTelegram');
    if (btnSimulateTelegram) {
        btnSimulateTelegram.addEventListener('click', async () => {
            tgTestStatus.innerText = '⏳ Simulating edge dispatch pipeline...';
            tgTestStatus.style.color = '#38BDF8';
            try {
                const formData = new FormData();
                formData.append('mock', 'true');
                const res = await fetch('/api/telegram/test', { method: 'POST', body: formData });
                const data = await res.json();
                tgTestStatus.innerText = data.message || '✅ Demo dispatch simulated successfully!';
                tgTestStatus.style.color = '#10B981';
            } catch (e) {
                tgTestStatus.innerText = '❌ Simulation error.';
                tgTestStatus.style.color = '#EF4444';
            }
        });
    }

    // ================= 16. Construction & Industrial AI Modules Modal =================
    const industrialModulesModal = document.getElementById('industrialModulesModal');
    const btnIndustrialModulesModal = document.getElementById('btnIndustrialModulesModal');
    const btnCloseIndustrialModules = document.getElementById('btnCloseIndustrialModules');
    const btnCancelIndustrialModules = document.getElementById('btnCancelIndustrialModules');

    const chkHeightSafety = document.getElementById('chkHeightSafety');
    const chkSuspendedLoad = document.getElementById('chkSuspendedLoad');
    const chkConfinedSpace = document.getElementById('chkConfinedSpace');
    const inputConfinedName = document.getElementById('inputConfinedName');
    const inputConfinedMinutes = document.getElementById('inputConfinedMinutes');
    const btnResetConfinedHeadcount = document.getElementById('btnResetConfinedHeadcount');
    const chkHotWork = document.getElementById('chkHotWork');
    const chkTrenchSafety = document.getElementById('chkTrenchSafety');
    const chkNightMode = document.getElementById('chkNightMode');

    async function loadModuleStates() {
        try {
            const res = await fetch('/api/modules/status');
            if (!res.ok) return;
            const data = await res.json();
            if (chkHeightSafety) chkHeightSafety.checked = !!data.height_safety;
            if (chkSuspendedLoad) chkSuspendedLoad.checked = !!data.suspended_load;
            if (chkConfinedSpace) {
                chkConfinedSpace.checked = !!data.confined_space?.enabled;
                if (data.confined_space?.name) inputConfinedName.value = data.confined_space.name;
                if (data.confined_space?.safe_minutes) inputConfinedMinutes.value = data.confined_space.safe_minutes;
            }
            if (chkHotWork) chkHotWork.checked = !!data.hot_work;
            if (chkTrenchSafety) chkTrenchSafety.checked = !!data.trench_safety;
            if (chkNightMode) chkNightMode.checked = !!data.night_mode;
        } catch (e) {
            console.warn('Failed to fetch module statuses:', e);
        }
    }

    if (btnIndustrialModulesModal) {
        btnIndustrialModulesModal.addEventListener('click', () => {
            loadModuleStates();
            industrialModulesModal.style.display = 'flex';
        });
    }

    if (btnCloseIndustrialModules) btnCloseIndustrialModules.addEventListener('click', () => industrialModulesModal.style.display = 'none');
    if (btnCancelIndustrialModules) btnCancelIndustrialModules.addEventListener('click', () => industrialModulesModal.style.display = 'none');

    async function toggleModuleApi(moduleName, isEnabled, param = null) {
        const formData = new FormData();
        formData.append('module', moduleName);
        formData.append('enabled', isEnabled ? 'true' : 'false');
        if (param) formData.append('param', param);
        await fetch('/api/modules/toggle', { method: 'POST', body: formData });
    }

    if (chkHeightSafety) {
        chkHeightSafety.addEventListener('change', () => toggleModuleApi('height_safety', chkHeightSafety.checked));
    }
    if (chkSuspendedLoad) {
        chkSuspendedLoad.addEventListener('change', () => toggleModuleApi('suspended_load', chkSuspendedLoad.checked));
    }
    if (chkConfinedSpace) {
        chkConfinedSpace.addEventListener('change', () => {
            const name = inputConfinedName ? inputConfinedName.value.trim() : 'Underground Silo / Manhole #4';
            toggleModuleApi('confined_space', chkConfinedSpace.checked, name);
        });
    }
    if (btnResetConfinedHeadcount) {
        btnResetConfinedHeadcount.addEventListener('click', async () => {
            await fetch('/api/confined-space/reset', { method: 'POST' });
            btnResetConfinedHeadcount.innerText = '✅ Headcount Reset (0)';
            setTimeout(() => { btnResetConfinedHeadcount.innerText = '🔄 Reset Headcount (0)'; }, 1500);
        });
    }
    if (chkHotWork) {
        chkHotWork.addEventListener('change', () => toggleModuleApi('hot_work', chkHotWork.checked));
    }
    if (chkTrenchSafety) {
        chkTrenchSafety.addEventListener('change', () => toggleModuleApi('trench_safety', chkTrenchSafety.checked));
    }
    if (chkNightMode) {
        chkNightMode.addEventListener('change', () => toggleModuleApi('night_mode', chkNightMode.checked));
    }

    // Initial load of module settings
    loadModuleStates();

    // ================= 17. Master Feature Switchboard & Auto-Pilot Mode =================
    const masterControlModal = document.getElementById('masterControlModal');
    const btnMasterControlModal = document.getElementById('btnMasterControlModal');
    const btnCloseMasterControl = document.getElementById('btnCloseMasterControl');
    const btnCancelMasterControl = document.getElementById('btnCancelMasterControl');

    const btnAutoPilotToggle = document.getElementById('btnAutoPilotToggle');
    const autoPilotText = document.getElementById('autoPilotText');
    const autoPilotBanner = document.getElementById('autoPilotBanner');
    const btnDisarmAutoPilot = document.getElementById('btnDisarmAutoPilot');

    // Switchboard Checkboxes
    const masterCheckboxes = {
        helmet_check: document.getElementById('chkMasterHelmet'),
        vest_check: document.getElementById('chkMasterVest'),
        height_safety: document.getElementById('chkMasterHarness'),
        fall_detection: document.getElementById('chkMasterFall'),
        phone_detection: document.getElementById('chkMasterPhone'),
        proximity_detection: document.getElementById('chkMasterProximity'),
        danger_zone: document.getElementById('chkMasterGeofence'),
        suspended_load: document.getElementById('chkMasterDropZone'),
        trench_safety: document.getElementById('chkMasterTrench'),
        gate_mode: document.getElementById('chkMasterGate'),
        fire_detection: document.getElementById('chkMasterFire'),
        hot_work: document.getElementById('chkMasterHotWork'),
        confined_space: document.getElementById('chkMasterConfined'),
        siren_audio: document.getElementById('chkMasterSiren'),
        telegram_alert: document.getElementById('chkMasterTelegram'),
        night_mode: document.getElementById('chkMasterNight')
    };

    // Live On-Dashboard Ribbon Chips
    const ribbonChips = {
        helmet_check: document.getElementById('chipHelmet'),
        vest_check: document.getElementById('chipVest'),
        height_safety: document.getElementById('chipHarness'),
        fall_detection: document.getElementById('chipFall'),
        phone_detection: document.getElementById('chipPhone'),
        proximity_detection: document.getElementById('chipProximity'),
        danger_zone: document.getElementById('chipGeofence'),
        suspended_load: document.getElementById('chipDropZone'),
        trench_safety: document.getElementById('chipTrench'),
        fire_detection: document.getElementById('chipFire'),
        hot_work: document.getElementById('chipHotWork'),
        confined_space: document.getElementById('chipConfined'),
        siren_audio: document.getElementById('chipSiren'),
        telegram_alert: document.getElementById('chipTelegram'),
        night_mode: document.getElementById('chipNight')
    };

    let currentFeatureMatrix = {};
    let isAutoPilotActive = false;

    function syncMasterControlsFromMatrix(matrix) {
        if (!matrix) return;
        currentFeatureMatrix = matrix;
        isAutoPilotActive = !!matrix.auto_pilot_mode;

        // Auto-Pilot UI updates
        if (autoPilotBanner) {
            autoPilotBanner.style.display = isAutoPilotActive ? 'flex' : 'none';
        }
        if (autoPilotText) {
            autoPilotText.innerText = isAutoPilotActive ? 'AUTO: ON' : 'AUTO: OFF';
        }
        if (btnAutoPilotToggle) {
            if (isAutoPilotActive) {
                btnAutoPilotToggle.classList.add('active-autopilot');
            } else {
                btnAutoPilotToggle.classList.remove('active-autopilot');
            }
        }

        // Update modal switchboard checkboxes
        for (const [key, element] of Object.entries(masterCheckboxes)) {
            if (element && matrix[key] !== undefined) {
                element.checked = !!matrix[key];
            }
        }

        // Update on-dashboard live ribbon chips
        for (const [key, chip] of Object.entries(ribbonChips)) {
            if (chip && matrix[key] !== undefined) {
                if (matrix[key]) {
                    chip.classList.add('active');
                } else {
                    chip.classList.remove('active');
                }
            }
        }

        // Update site modules modal checkboxes in sync
        if (chkHeightSafety && matrix.height_safety !== undefined) chkHeightSafety.checked = !!matrix.height_safety;
        if (chkSuspendedLoad && matrix.suspended_load !== undefined) chkSuspendedLoad.checked = !!matrix.suspended_load;
        if (chkConfinedSpace && matrix.confined_space !== undefined) chkConfinedSpace.checked = !!matrix.confined_space;
        if (chkHotWork && matrix.hot_work !== undefined) chkHotWork.checked = !!matrix.hot_work;
        if (chkTrenchSafety && matrix.trench_safety !== undefined) chkTrenchSafety.checked = !!matrix.trench_safety;
        if (chkNightMode && matrix.night_mode !== undefined) chkNightMode.checked = !!matrix.night_mode;
    }

    async function loadMasterControlStatus() {
        try {
            const res = await fetch('/api/master-control/status');
            if (!res.ok) return;
            const data = await res.json();
            if (data.matrix) {
                syncMasterControlsFromMatrix(data.matrix);
            }
        } catch (e) {
            console.warn('Failed to load master control status:', e);
        }
    }

    async function toggleMasterFeature(featureKey, enabled) {
        try {
            // Optimistically update local UI immediately
            if (masterCheckboxes[featureKey]) {
                masterCheckboxes[featureKey].checked = enabled;
            }
            if (ribbonChips[featureKey]) {
                if (enabled) ribbonChips[featureKey].classList.add('active');
                else ribbonChips[featureKey].classList.remove('active');
            }

            const formData = new FormData();
            formData.append('feature', featureKey);
            formData.append('enabled', enabled ? 'true' : 'false');
            const res = await fetch('/api/master-control/toggle', { method: 'POST', body: formData });
            if (res.ok) {
                const data = await res.json();
                if (data.matrix) {
                    syncMasterControlsFromMatrix(data.matrix);
                }
            }
        } catch (e) {
            console.error(`Failed to toggle ${featureKey}:`, e);
        }
    }

    async function applyOperationalPreset(presetName) {
        try {
            // Instant active preset highlight across all preset buttons
            const allPresetBtns = document.querySelectorAll('.preset-btn');
            allPresetBtns.forEach(btn => {
                if (btn.getAttribute('data-preset') === presetName) {
                    btn.classList.add('active-preset');
                } else {
                    btn.classList.remove('active-preset');
                }
            });

            const formData = new FormData();
            formData.append('preset_name', presetName);
            const res = await fetch('/api/master-control/preset', { method: 'POST', body: formData });
            if (res.ok) {
                const data = await res.json();
                if (data.matrix) {
                    syncMasterControlsFromMatrix(data.matrix);
                }
            }
        } catch (e) {
            console.error(`Failed to apply preset ${presetName}:`, e);
        }
    }

    // Modal Triggers
    if (btnMasterControlModal) {
        btnMasterControlModal.addEventListener('click', () => {
            loadMasterControlStatus();
            masterControlModal.style.display = 'flex';
        });
    }

    const btnBackMasterControl = document.getElementById('btnBackMasterControl');

    if (btnCloseMasterControl) btnCloseMasterControl.addEventListener('click', () => masterControlModal.style.display = 'none');
    if (btnBackMasterControl) btnBackMasterControl.addEventListener('click', () => masterControlModal.style.display = 'none');
    if (btnCancelMasterControl) btnCancelMasterControl.addEventListener('click', () => masterControlModal.style.display = 'none');

    // Close on backdrop click (click outside modal box)
    if (masterControlModal) {
        masterControlModal.addEventListener('click', (e) => {
            if (e.target === masterControlModal) {
                masterControlModal.style.display = 'none';
            }
        });
    }

    // Close on Escape key press
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
            if (masterControlModal && masterControlModal.style.display === 'flex') {
                masterControlModal.style.display = 'none';
            }
        }
    });

    // Tools Dropdown Menu Controller
    const btnToolsMenu = document.getElementById('btnToolsMenu');
    const toolsMenuContent = document.getElementById('toolsMenuContent');
    if (btnToolsMenu && toolsMenuContent) {
        btnToolsMenu.addEventListener('click', (e) => {
            e.stopPropagation();
            toolsMenuContent.classList.toggle('show-menu');
        });

        // Close on clicking outside
        document.addEventListener('click', (e) => {
            if (!toolsMenuContent.contains(e.target) && e.target !== btnToolsMenu) {
                toolsMenuContent.classList.remove('show-menu');
            }
        });

        // Auto-close menu when any dropdown item is clicked
        const menuItems = toolsMenuContent.querySelectorAll('.dropdown-menu-item');
        menuItems.forEach(item => {
            item.addEventListener('click', () => {
                toolsMenuContent.classList.remove('show-menu');
            });
        });
    }

    // Mobile Navigation Controls Toggle
    const btnNavToggle = document.getElementById('btnNavToggle');
    const navActions = document.getElementById('navActions');
    if (btnNavToggle && navActions) {
        btnNavToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            navActions.classList.toggle('is-collapsed');
            const arrow = btnNavToggle.querySelector('.toggle-arrow');
            if (arrow) {
                arrow.innerText = navActions.classList.contains('is-collapsed') ? '▾' : '▴';
            }
        });
    }

    // Auto-Pilot Button Handlers
    if (btnAutoPilotToggle) {
        btnAutoPilotToggle.addEventListener('click', () => {
            if (isAutoPilotActive) {
                applyOperationalPreset('clean_ppe_only');
            } else {
                applyOperationalPreset('auto_pilot');
            }
        });
    }

    if (btnDisarmAutoPilot) {
        btnDisarmAutoPilot.addEventListener('click', () => {
            applyOperationalPreset('clean_ppe_only');
        });
    }

    // Preset Buttons Click Listeners (both ribbon and modal)
    const presetButtons = document.querySelectorAll('.preset-btn');
    presetButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const preset = btn.getAttribute('data-preset');
            if (preset) {
                applyOperationalPreset(preset);
            }
        });
    });

    // On-Dashboard Quick Ribbon Chips Click Handler
    const chipButtons = document.querySelectorAll('.chip-toggle[data-feature]');
    chipButtons.forEach(chip => {
        chip.addEventListener('click', (e) => {
            e.preventDefault();
            const featureKey = chip.getAttribute('data-feature');
            const willEnable = !chip.classList.contains('active');
            toggleMasterFeature(featureKey, willEnable);
        });
    });

    // Entire Modal Row Click Handler
    const switchRows = document.querySelectorAll('.switch-row[data-toggle]');
    switchRows.forEach(row => {
        row.addEventListener('click', (e) => {
            if (e.target.tagName === 'INPUT') return;
            const featureKey = row.getAttribute('data-toggle');
            const input = row.querySelector('input[type="checkbox"]');
            if (input && featureKey) {
                input.checked = !input.checked;
                toggleMasterFeature(featureKey, input.checked);
            }
        });
    });

    // Direct Modal Checkbox Change Listeners
    for (const [key, element] of Object.entries(masterCheckboxes)) {
        if (element) {
            element.addEventListener('change', () => {
                toggleMasterFeature(key, element.checked);
            });
        }
    }

    // Top Bar Gate Mode Toggle Handler
    const btnGateModeToggleElement = document.getElementById('btnGateModeToggle');
    if (btnGateModeToggleElement) {
        btnGateModeToggleElement.addEventListener('click', () => {
            const willEnable = !btnGateModeToggleElement.classList.contains('active');
            toggleMasterFeature('gate_mode', willEnable);
            if (toolsMenuContent) toolsMenuContent.classList.remove('show-menu');
        });
    }

    // ================= AI Detection Sensitivity Controller =================
    const btnQuickSensitivity = document.getElementById('btnQuickSensitivity');
    const navSensitivityText = document.getElementById('navSensitivityText');
    const sensitivityLivePill = document.getElementById('sensitivityLivePill');
    const sensitivityPillText = document.getElementById('sensitivityPillText');
    const sensPresetButtons = document.querySelectorAll('.btn-sens-preset');
    const sliderConfidence = document.getElementById('sliderConfidence');
    const lblConfidenceVal = document.getElementById('lblConfidenceVal');
    const sliderCooldown = document.getElementById('sliderCooldown');
    const lblCooldownVal = document.getElementById('lblCooldownVal');

    let currentSensitivityLevel = 'ultra';
    let currentConfThresh = 0.15;
    let currentCooldown = 1.5;

    function renderSensitivityUI(level, conf, cooldown) {
        currentSensitivityLevel = level || currentSensitivityLevel;
        if (conf !== undefined && conf !== null) currentConfThresh = parseFloat(conf);
        if (cooldown !== undefined && cooldown !== null) currentCooldown = parseFloat(cooldown);

        const confPct = Math.round(currentConfThresh * 100);

        // 1. Update Navbar Button Text & Accent
        if (navSensitivityText) {
            navSensitivityText.innerText = currentSensitivityLevel.toUpperCase();
        }
        if (btnQuickSensitivity) {
            btnQuickSensitivity.style.borderColor = currentSensitivityLevel === 'ultra' ? '#EF4444' : (currentSensitivityLevel === 'high' ? '#F59E0B' : '#10B981');
        }

        // 2. Update Modal Live Pill
        if (sensitivityPillText) {
            if (currentSensitivityLevel === 'ultra') {
                sensitivityPillText.innerText = `ULTRA STRICT (${confPct}% CONF)`;
                if (sensitivityLivePill) {
                    sensitivityLivePill.style.borderColor = 'rgba(239, 68, 68, 0.6)';
                    sensitivityLivePill.style.color = '#FCA5A5';
                }
            } else if (currentSensitivityLevel === 'high') {
                sensitivityPillText.innerText = `HIGH SENSITIVITY (${confPct}% CONF)`;
                if (sensitivityLivePill) {
                    sensitivityLivePill.style.borderColor = 'rgba(245, 158, 11, 0.6)';
                    sensitivityLivePill.style.color = '#FDE68A';
                }
            } else {
                sensitivityPillText.innerText = `STANDARD BALANCED (${confPct}% CONF)`;
                if (sensitivityLivePill) {
                    sensitivityLivePill.style.borderColor = 'rgba(16, 185, 129, 0.6)';
                    sensitivityLivePill.style.color = '#A7F3D0';
                }
            }
        }

        // 3. Update Preset Buttons
        sensPresetButtons.forEach(btn => {
            const mode = btn.getAttribute('data-sens');
            if (mode === currentSensitivityLevel) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        // 4. Update Sliders and Numeric Labels
        if (sliderConfidence) sliderConfidence.value = currentConfThresh;
        if (lblConfidenceVal) lblConfidenceVal.innerText = `${confPct}% (${currentConfThresh.toFixed(2)})`;
        if (sliderCooldown) sliderCooldown.value = currentCooldown;
        if (lblCooldownVal) lblCooldownVal.innerText = `${currentCooldown.toFixed(1)}s ${currentCooldown <= 1.5 ? '(Instant)' : ''}`;
    }

    async function sendSensitivityUpdate(params) {
        try {
            const formData = new FormData();
            if (params.level) formData.append('level', params.level);
            if (params.conf_thresh !== undefined) formData.append('conf_thresh', params.conf_thresh);
            if (params.cooldown !== undefined) formData.append('cooldown', params.cooldown);

            const res = await fetch('/api/sensitivity', {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                const data = await res.json();
                renderSensitivityUI(data.level, data.conf_thresh, data.cooldown);
            }
        } catch (err) {
            console.error('[Sensitivity Update Error]', err);
        }
    }

    // Quick Navbar Toggle Cycle: standard -> high -> ultra -> standard
    if (btnQuickSensitivity) {
        btnQuickSensitivity.addEventListener('click', () => {
            let nextLevel = 'ultra';
            if (currentSensitivityLevel === 'ultra') nextLevel = 'standard';
            else if (currentSensitivityLevel === 'standard') nextLevel = 'high';
            else nextLevel = 'ultra';

            sendSensitivityUpdate({ level: nextLevel });
        });
    }

    // Preset Buttons Click
    sensPresetButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const sens = btn.getAttribute('data-sens');
            if (sens) {
                sendSensitivityUpdate({ level: sens });
            }
        });
    });

    // Confidence Slider Realtime Input & Change
    if (sliderConfidence) {
        sliderConfidence.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            const pct = Math.round(val * 100);
            if (lblConfidenceVal) lblConfidenceVal.innerText = `${pct}% (${val.toFixed(2)})`;
        });
        sliderConfidence.addEventListener('change', (e) => {
            const val = parseFloat(e.target.value);
            sendSensitivityUpdate({ conf_thresh: val });
        });
    }

    // Cooldown Slider Realtime Input & Change
    if (sliderCooldown) {
        sliderCooldown.addEventListener('input', (e) => {
            const val = parseFloat(e.target.value);
            if (lblCooldownVal) lblCooldownVal.innerText = `${val.toFixed(1)}s ${val <= 1.5 ? '(Instant)' : ''}`;
        });
        sliderCooldown.addEventListener('change', (e) => {
            const val = parseFloat(e.target.value);
            sendSensitivityUpdate({ cooldown: val });
        });
    }

    // Initial fetch of sensitivity status
    async function loadSensitivityStatus() {
        try {
            const res = await fetch('/api/sensitivity');
            if (res.ok) {
                const data = await res.json();
                renderSensitivityUI(data.level, data.conf_thresh, data.cooldown);
            }
        } catch (e) {
            console.warn('[Sensitivity Status Fetch]', e);
        }
    }
    loadSensitivityStatus();

    // Initial load
    loadMasterControlStatus();

    // ================= 19. Web Audio API Acoustic Sound Synthesizer =================
    let webAudioCtx = null;
    function getAudioContext() {
        if (!webAudioCtx) {
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            if (AudioCtx) webAudioCtx = new AudioCtx();
        }
        if (webAudioCtx && webAudioCtx.state === 'suspended') {
            webAudioCtx.resume();
        }
        return webAudioCtx;
    }

    function playClientAcousticTone(featureKey) {
        try {
            const ctx = getAudioContext();
            if (!ctx) return;
            const now = ctx.currentTime;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            const key = (featureKey || '').toLowerCase();
            if (key === 'fire') {
                // European two-tone emergency warble (950Hz alternating with 650Hz)
                osc.type = 'sawtooth';
                gain.gain.setValueAtTime(0.2, now);
                for (let i = 0; i < 4; i++) {
                    osc.frequency.setValueAtTime(950, now + i * 0.35);
                    osc.frequency.setValueAtTime(650, now + i * 0.35 + 0.18);
                }
                gain.gain.exponentialRampToValueAtTime(0.01, now + 1.45);
                osc.start(now);
                osc.stop(now + 1.5);
            } else if (key === 'fall') {
                // Low medical descending distress frequency (460Hz down to 240Hz)
                osc.type = 'triangle';
                gain.gain.setValueAtTime(0.3, now);
                osc.frequency.setValueAtTime(460, now);
                osc.frequency.exponentialRampToValueAtTime(240, now + 1.1);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 1.25);
                osc.start(now);
                osc.stop(now + 1.3);
            } else if (key === 'harness') {
                // Sharp high-pitch double pulse (1350Hz)
                osc.type = 'square';
                osc.frequency.setValueAtTime(1350, now);
                gain.gain.setValueAtTime(0.25, now);
                gain.gain.setValueAtTime(0, now + 0.2);
                gain.gain.setValueAtTime(0.25, now + 0.32);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
                osc.start(now);
                osc.stop(now + 0.65);
            } else if (key === 'crane' || key === 'suspended_load') {
                // Triple staccato drop hazard horn (1150Hz)
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(1150, now);
                gain.gain.setValueAtTime(0.25, now);
                gain.gain.setValueAtTime(0, now + 0.16);
                gain.gain.setValueAtTime(0.25, now + 0.26);
                gain.gain.setValueAtTime(0, now + 0.42);
                gain.gain.setValueAtTime(0.25, now + 0.52);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.78);
                osc.start(now);
                osc.stop(now + 0.8);
            } else if (key === 'gate_pass') {
                // Harmonious ascending entrance chime (C5 -> E5 -> G5 -> C6)
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.22, now);
                osc.frequency.setValueAtTime(523.25, now);
                osc.frequency.setValueAtTime(659.25, now + 0.12);
                osc.frequency.setValueAtTime(783.99, now + 0.24);
                osc.frequency.setValueAtTime(1046.50, now + 0.36);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.7);
                osc.start(now);
                osc.stop(now + 0.75);
            } else if (key === 'gate_fail') {
                // Low descending denied buzzer (320Hz -> 200Hz)
                osc.type = 'sawtooth';
                gain.gain.setValueAtTime(0.3, now);
                osc.frequency.setValueAtTime(320, now);
                gain.gain.setValueAtTime(0, now + 0.18);
                gain.gain.setValueAtTime(0.3, now + 0.28);
                osc.frequency.setValueAtTime(200, now + 0.28);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.6);
                osc.start(now);
                osc.stop(now + 0.65);
            } else if (key === 'helmet' || key === 'vest') {
                // PPE rising chirp (780Hz -> 980Hz)
                osc.type = 'sine';
                gain.gain.setValueAtTime(0.25, now);
                osc.frequency.setValueAtTime(780, now);
                osc.frequency.linearRampToValueAtTime(980, now + 0.3);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.45);
                osc.start(now);
                osc.stop(now + 0.5);
            } else if (key === 'geofence' || key === 'night') {
                // Alternating security siren (980Hz / 1180Hz)
                osc.type = 'sawtooth';
                gain.gain.setValueAtTime(0.25, now);
                osc.frequency.setValueAtTime(980, now);
                osc.frequency.setValueAtTime(1180, now + 0.25);
                osc.frequency.setValueAtTime(980, now + 0.5);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.75);
                osc.start(now);
                osc.stop(now + 0.8);
            } else if (key === 'phone') {
                // Triple staccato chirp (1200Hz)
                osc.type = 'square';
                gain.gain.setValueAtTime(0.2, now);
                osc.frequency.setValueAtTime(1200, now);
                gain.gain.setValueAtTime(0, now + 0.1);
                gain.gain.setValueAtTime(0.2, now + 0.18);
                gain.gain.setValueAtTime(0, now + 0.28);
                gain.gain.setValueAtTime(0.2, now + 0.36);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.55);
                osc.start(now);
                osc.stop(now + 0.6);
            } else {
                // Standard clean industrial pulse (880Hz)
                osc.type = 'square';
                gain.gain.setValueAtTime(0.2, now);
                osc.frequency.setValueAtTime(880, now);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
                osc.start(now);
                osc.stop(now + 0.45);
            }
        } catch (e) {
            console.warn('[AudioSynth Error]', e);
        }
    }

    // ================= 20. Feature Showcase Gallery & Siren Testing Hub =================
    const featureGalleryModal = document.getElementById('featureGalleryModal');
    const btnOpenFeatureGallery = document.getElementById('btnOpenFeatureGallery');
    const btnMenuFeatureGallery = document.getElementById('btnMenuFeatureGallery');
    const btnCloseFeatureGallery = document.getElementById('btnCloseFeatureGallery');
    const btnCancelFeatureGallery = document.getElementById('btnCancelFeatureGallery');
    const btnGalleryOpenScorecard = document.getElementById('btnGalleryOpenScorecard');

    function openFeatureGallery() {
        if (featureGalleryModal) {
            featureGalleryModal.style.display = 'flex';
        }
    }

    function closeFeatureGallery() {
        if (featureGalleryModal) {
            featureGalleryModal.style.display = 'none';
        }
    }

    if (btnOpenFeatureGallery) btnOpenFeatureGallery.addEventListener('click', openFeatureGallery);
    if (btnMenuFeatureGallery) btnMenuFeatureGallery.addEventListener('click', openFeatureGallery);
    if (btnCloseFeatureGallery) btnCloseFeatureGallery.addEventListener('click', closeFeatureGallery);
    if (btnCancelFeatureGallery) btnCancelFeatureGallery.addEventListener('click', closeFeatureGallery);

    // Scorecard navigation from gallery card
    if (btnGalleryOpenScorecard) {
        btnGalleryOpenScorecard.addEventListener('click', () => {
            closeFeatureGallery();
            const scorecardModal = document.getElementById('scorecardModal');
            if (scorecardModal) {
                scorecardModal.style.display = 'flex';
                const btnRefreshScorecard = document.getElementById('btnRefreshScorecard');
                if (btnRefreshScorecard) btnRefreshScorecard.click();
            }
        });
    }

    // Telegram config navigation from gallery card
    const btnGalleryOpenTelegram = document.getElementById('btnGalleryOpenTelegram');
    if (btnGalleryOpenTelegram) {
        btnGalleryOpenTelegram.addEventListener('click', () => {
            closeFeatureGallery();
            const telegramModal = document.getElementById('telegramModal');
            if (telegramModal) {
                telegramModal.style.display = 'flex';
                if (btnTelegramModal) btnTelegramModal.click();
            }
        });
    }

    // Category Filter Pills
    const filterPills = document.querySelectorAll('.gallery-filter-pill');
    const galleryCards = document.querySelectorAll('.gallery-card');

    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');

            const filter = pill.getAttribute('data-filter') || 'all';
            galleryCards.forEach(card => {
                const category = card.getAttribute('data-category');
                if (filter === 'all' || category === filter) {
                    card.style.display = 'flex';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });

    // Dedicated Siren Play Trigger Handler (both in Feature Gallery & Industrial Modules Modal)
    async function triggerFeatureSiren(key, targetBtn) {
        if (!key) return;
        
        // 1. Play local Web Audio synthesizer immediate feedback
        playClientAcousticTone(key);

        // 2. Visual feedback on button
        const originalText = targetBtn.innerText;
        targetBtn.classList.add('playing');
        targetBtn.innerText = '📢 Sounding...';

        // 3. Trigger physical edge server siren & TTS voice via API
        try {
            await fetch(`/api/alarm/test/${encodeURIComponent(key)}`, { method: 'POST' });
        } catch (e) {
            console.warn('[Feature Siren Trigger API Error]', e);
        }

        // 4. Reset button after 2.5 seconds
        setTimeout(() => {
            targetBtn.classList.remove('playing');
            targetBtn.innerText = originalText;
        }, 2500);
    }

    // Bind all siren buttons in Feature Gallery (.btn-siren-play)
    document.querySelectorAll('.btn-siren-play').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const sirenKey = btn.getAttribute('data-siren-key');
            triggerFeatureSiren(sirenKey, btn);
        });
    });

    // Bind all siren test buttons in Industrial Modules Modal (.btn-siren-test)
    document.querySelectorAll('.btn-siren-test').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const sirenKey = btn.getAttribute('data-test-siren');
            triggerFeatureSiren(sirenKey, btn);
        });
    });
});



