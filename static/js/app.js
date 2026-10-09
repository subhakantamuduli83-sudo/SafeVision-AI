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
    let isDocumentVisible = true;
    document.addEventListener('visibilitychange', () => {
        isDocumentVisible = !document.hidden;
        if (isDocumentVisible) {
            fetchStats();
            fetchIncidents();
            if (typeof refreshActiveZoneCameras === 'function') refreshActiveZoneCameras();
        }
    });

    async function fetchStats() {
        if (!isDocumentVisible) return;
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

            // Edge Hardware Accelerator Dynamic Status
            const processorEl = document.getElementById('sidebarProcessorVal');
            if (processorEl && data.intel_mode) {
                processorEl.innerText = data.intel_mode.includes('NPU') ? 'Intel(R) NPU + GPU ⚡' : data.intel_mode;
                processorEl.title = data.intel_mode;
            }

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
        if (!isDocumentVisible) return;
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
    window.triggerSpeakerSirenTest = async function(btn) {
        const targetBtn = btn || document.getElementById('btnAudioTest');
        const origText = targetBtn ? targetBtn.innerText : '🔊 Test Speaker Siren';
        if (targetBtn) {
            targetBtn.innerText = '🔊 Siren Active...';
            targetBtn.classList.add('playing');
            targetBtn.disabled = true;
        }

        // 1. Play local browser Web Audio synthesizer
        try {
            if (typeof playClientAcousticTone === 'function') {
                playClientAcousticTone('master');
            } else if (typeof window.playClientAcousticTone === 'function') {
                window.playClientAcousticTone('master');
            }
        } catch (e) {
            console.warn('[Audio Siren] Web Audio error:', e);
        }

        // 2. Play server hardware speaker / TTS alert
        try {
            const formData = new FormData();
            formData.append('trigger_test', 'true');
            await fetch('/api/alarm/toggle', { method: 'POST', body: formData });
        } catch (err) {
            console.warn('[Audio Siren] Toggle alarm error:', err);
        }

        // 3. Reset button after 2.2 seconds
        setTimeout(() => {
            if (targetBtn) {
                targetBtn.innerText = origText;
                targetBtn.classList.remove('playing');
                targetBtn.disabled = false;
            }
        }, 2200);
    };

    if (btnAudioTest) {
        btnAudioTest.addEventListener('click', (e) => {
            e.preventDefault();
            window.triggerSpeakerSirenTest(btnAudioTest);
        });
    }

    document.querySelectorAll('.btn-audio-test').forEach(b => {
        b.addEventListener('click', (e) => {
            e.preventDefault();
            window.triggerSpeakerSirenTest(b);
        });
    });

    btnMuteToggle.addEventListener('click', async () => {
        isMuted = !isMuted;
        const formData = new FormData();
        formData.append('mute', isMuted ? 'true' : 'false');
        await fetch('/api/alarm/toggle', { method: 'POST', body: formData });
        muteStatusText.innerText = isMuted ? 'MUTED' : 'ON';
    });

    // 1-Click Server Shutdown Switch
    const btnSystemShutdown = document.getElementById('btnSystemShutdown');
    if (btnSystemShutdown) {
        btnSystemShutdown.addEventListener('click', async () => {
            if (confirm("Kya aap SafeVision AI ko band karna chahte hain?\n\n(Are you sure you want to stop SafeVision AI?)")) {
                btnSystemShutdown.disabled = true;
                btnSystemShutdown.innerText = "Stopping...";
                try {
                    await fetch('/api/system/shutdown', { method: 'POST' });
                } catch (e) {
                    // Ignore disconnect on shutdown
                }
                document.body.innerHTML = `
                    <div style="height: 100vh; display: flex; flex-direction: column; align-items: center; justify-content: center; background: #070d18; color: #f87171; font-family: 'Inter', sans-serif; text-align: center; padding: 24px;">
                        <div style="font-size: 4rem; margin-bottom: 12px;">⏻</div>
                        <h1 style="font-size: 2.2rem; margin-bottom: 8px; color: #f1f5f9;">SafeVision AI Server Stopped</h1>
                        <p style="color: #94a3b8; font-size: 1.1rem; max-width: 480px; line-height: 1.5;">Server aur AI cameras safely band ho chuke hain. Aap is browser tab ko close kar sakte hain.</p>
                        <button onclick="window.close()" style="margin-top: 24px; padding: 10px 24px; background: #0ea5e9; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 1rem;">Close Window</button>
                    </div>
                `;
            }
        });
    }

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
    window.openDroidCamModal = function() {
        if (cameraModal) {
            cameraModal.style.display = 'flex';
        }
        if (sourceSelect) {
            sourceSelect.value = 'droidcam-wifi';
            sourceSelect.dispatchEvent(new Event('change'));
        }
        if (urlInputLabel) {
            urlInputLabel.innerText = 'DroidCam Wi-Fi Stream URL:';
        }
        if (modalUrlInput) {
            modalUrlInput.value = 'http://192.168.1.15:4747/video';
            modalUrlInput.placeholder = 'http://192.168.1.15:4747/video';
            setTimeout(() => {
                modalUrlInput.focus();
                modalUrlInput.select();
            }, 100);
        }
        if (cameraHelperText) {
            cameraHelperText.innerHTML = '💡 <b>DroidCam Wi-Fi:</b> Open DroidCam on phone, connect to same Wi-Fi/Hotspot, and enter the IP shown on phone (e.g. <code>http://192.168.1.15:4747/video</code>).';
        }
    };

    const btnConnectDroidCam = document.getElementById('btnConnectDroidCam');
    if (btnConnectDroidCam) {
        btnConnectDroidCam.addEventListener('click', (e) => {
            e.preventDefault();
            window.openDroidCamModal();
        });
    }

    if (btnCameraSettings) {
        btnCameraSettings.addEventListener('click', () => {
            cameraModal.style.display = 'flex';
        });
    }

    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', () => {
            cameraModal.style.display = 'none';
        });
    }

    if (btnCancelModal) {
        btnCancelModal.addEventListener('click', () => {
            cameraModal.style.display = 'none';
        });
    }

    if (cameraModal) {
        cameraModal.addEventListener('click', (e) => {
            if (e.target === cameraModal) {
                cameraModal.style.display = 'none';
            }
        });
    }

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
        const submitBtn = cameraConfigForm.querySelector('button[type="submit"]');
        const origBtnText = submitBtn ? submitBtn.innerText : 'Apply & Connect';
        if (submitBtn) {
            submitBtn.innerText = 'Connecting...';
            submitBtn.disabled = true;
        }

        const sourceVal = modalUrlInput.value.trim();
        const zoneVal = zoneInput.value.trim();

        try {
            const formData = new FormData();
            formData.append('source', sourceVal);
            formData.append('zone', zoneVal);

            await fetch('/api/settings', { method: 'POST', body: formData });
            cameraModal.style.display = 'none';
            if (quickSourceInput) quickSourceInput.value = sourceVal;
            if (liveVideoFeed) liveVideoFeed.src = `/video_feed?t=${new Date().getTime()}`;

            // Switch to Live Vision view so user immediately sees their camera
            if (typeof window.switchDashboardView === 'function') {
                window.switchDashboardView('view-live');
            }
        } catch (err) {
            console.error('Camera connection error:', err);
            alert('Could not apply camera settings: ' + err.message);
        } finally {
            if (submitBtn) {
                submitBtn.innerText = origBtnText;
                submitBtn.disabled = false;
            }
        }
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
        const bodies = document.querySelectorAll('#copilotChatBody');
        bodies.forEach(body => {
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
            body.appendChild(msgDiv);
            body.scrollTop = body.scrollHeight;
        });
    }

    async function sendCopilotQuery(query) {
        if (!query || !query.trim()) return;
        const q = query.trim();
        appendCopilotMessage('user', q);
        document.querySelectorAll('#copilotInput, .copilot-input-bar input').forEach(inp => inp.value = '');

        // Add thinking placeholder to all chat bodies
        const bodies = document.querySelectorAll('#copilotChatBody');
        bodies.forEach(body => {
            const thinkingDiv = document.createElement('div');
            thinkingDiv.className = 'chat-msg ai-msg copilot-thinking-item';
            thinkingDiv.innerHTML = '<div class="msg-avatar">🤖</div><div class="msg-content"><em>Analyzing factory telemetry & OSHA guidelines...</em></div>';
            body.appendChild(thinkingDiv);
            body.scrollTop = body.scrollHeight;
        });

        try {
            const formData = new FormData();
            formData.append('query', q);
            const res = await fetch('/api/copilot/chat', { method: 'POST', body: formData });
            const data = await res.json();
            
            document.querySelectorAll('.copilot-thinking-item').forEach(el => el.remove());
            appendCopilotMessage('ai', data.response, data.mode);
        } catch (e) {
            document.querySelectorAll('.copilot-thinking-item').forEach(el => el.remove());
            appendCopilotMessage('ai', 'Error connecting to Safety Copilot engine. Please retry.');
        }
    }

    // Support all Copilot chat bodies and input forms
    document.querySelectorAll('#copilotForm, .copilot-input-bar').forEach(form => {
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const inp = form.querySelector('input');
            if (inp && inp.value) {
                sendCopilotQuery(inp.value);
            }
        });
    });

    // Support both .chip-btn and .copilot-quick-chip
    document.querySelectorAll('.chip-btn, .copilot-quick-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const q = btn.getAttribute('data-query');
            if (q) sendCopilotQuery(q);
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
    const btnToggleTokenVisibility = document.getElementById('btnToggleTokenVisibility');

    if (btnToggleTokenVisibility && tgBotTokenInput) {
        btnToggleTokenVisibility.addEventListener('click', () => {
            if (tgBotTokenInput.type === 'password') {
                tgBotTokenInput.type = 'text';
                btnToggleTokenVisibility.innerText = '🔒 Hide Token';
            } else {
                tgBotTokenInput.type = 'password';
                btnToggleTokenVisibility.innerText = '👁️ Show Token';
            }
        });
    }

    if (btnTelegramModal) {
        btnTelegramModal.addEventListener('click', async () => {
            telegramModal.style.display = 'flex';
            tgTestStatus.innerText = '';
            try {
                const res = await fetch('/api/telegram/config');
                const data = await res.json();
                if (data.token && data.token !== 'dummy_token' && !data.token.includes('dummy')) {
                    tgBotTokenInput.value = data.token;
                } else if (!tgBotTokenInput.value) {
                    tgBotTokenInput.value = '';
                }

                if (data.chat_id && data.chat_id !== '12345' && data.chat_id !== '0') {
                    tgChatIdInput.value = data.chat_id;
                } else if (!tgChatIdInput.value) {
                    tgChatIdInput.value = '';
                }

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

            if (enabled && (!token || !chat_id)) {
                tgTestStatus.innerText = '⚠️ Please enter both Bot Token and numeric Chat ID to enable alerts!';
                tgTestStatus.style.color = '#F59E0B';
                return;
            }

            const formData = new FormData();
            formData.append('token', token);
            formData.append('chat_id', chat_id);
            formData.append('enabled', enabled ? 'true' : 'false');

            try {
                const res = await fetch('/api/telegram/config', { method: 'POST', body: formData });
                const data = await res.json();
                tgTestStatus.innerText = '✅ Telegram configuration saved!';
                tgTestStatus.style.color = '#10B981';

                // Sync UI controls
                if (masterCheckboxes.telegram_alert) {
                    masterCheckboxes.telegram_alert.checked = enabled && !!token && !!chat_id;
                }
                if (ribbonChips.telegram_alert) {
                    if (enabled && !!token && !!chat_id) ribbonChips.telegram_alert.classList.add('active');
                    else ribbonChips.telegram_alert.classList.remove('active');
                }
                loadMasterControlStatus();

                setTimeout(() => {
                    telegramModal.style.display = 'none';
                    tgTestStatus.innerText = '';
                }, 900);
            } catch (err) {
                tgTestStatus.innerText = '❌ Failed to save configuration: ' + err;
                tgTestStatus.style.color = '#EF4444';
            }
        });
    }

    if (btnTestTelegram) {
        btnTestTelegram.addEventListener('click', async () => {
            const token = tgBotTokenInput.value.trim();
            const chat_id = tgChatIdInput.value.trim();

            if (!token || !chat_id) {
                tgTestStatus.innerText = '⚠️ Please enter both Bot Token and Chat ID above first!';
                tgTestStatus.style.color = '#F59E0B';
                return;
            }

            tgTestStatus.innerText = '⏳ Connecting to Telegram API & sending live test alert...';
            tgTestStatus.style.color = '#38BDF8';

            try {
                const formData = new FormData();
                formData.append('token', token);
                formData.append('chat_id', chat_id);
                formData.append('enabled', 'true');

                const res = await fetch('/api/telegram/test', { method: 'POST', body: formData });
                const data = await res.json();
                if (data.status === 'success') {
                    tgTestStatus.innerText = '✅ Test alert delivered to your Telegram app!';
                    tgTestStatus.style.color = '#10B981';
                } else if (data.status === 'mock') {
                    tgTestStatus.innerText = `🧪 ${data.message}`;
                    tgTestStatus.style.color = '#38BDF8';
                } else {
                    tgTestStatus.innerText = `⚠️ ${data.message || 'Check Token & Chat ID'}`;
                    tgTestStatus.style.color = '#F59E0B';
                }
            } catch (e) {
                tgTestStatus.innerText = '❌ Error triggering alert: ' + e;
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
            if (featureKey === 'telegram_alert' && enabled) {
                try {
                    const cfgRes = await fetch('/api/telegram/config');
                    const cfg = await cfgRes.json();
                    if (!cfg.is_configured) {
                        if (btnTelegramModal) btnTelegramModal.click();
                        const statusEl = document.getElementById('tgTestStatus');
                        if (statusEl) {
                            statusEl.innerText = '👉 Please enter your Bot Token & Chat ID first to arm Telegram alerts!';
                            statusEl.style.color = '#F59E0B';
                        }
                        return;
                    }
                } catch (e) {}
            }

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
            const key = (featureKey || '').toLowerCase();

            function createSynth(type = 'sine') {
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = type;
                osc.connect(gain);
                gain.connect(ctx.destination);
                return { osc, gain };
            }

            // 1. MASTER SPEAKER / GENERAL TEST: Industrial Factory Air Horn / Klaxon (Sweeping Brass Power)
            if (key === 'general_test' || key === 'master' || key === 'speaker' || key === 'test') {
                const { osc: osc1, gain: g1 } = createSynth('sawtooth');
                const { osc: osc2, gain: g2 } = createSynth('sawtooth');
                
                g1.gain.setValueAtTime(0.01, now);
                g1.gain.linearRampToValueAtTime(0.35, now + 0.12);
                osc1.frequency.setValueAtTime(280, now);
                osc1.frequency.exponentialRampToValueAtTime(550, now + 0.28);
                osc1.frequency.setValueAtTime(550, now + 0.75);
                g1.gain.exponentialRampToValueAtTime(0.01, now + 1.2);

                g2.gain.setValueAtTime(0.01, now);
                g2.gain.linearRampToValueAtTime(0.25, now + 0.12);
                osc2.frequency.setValueAtTime(440, now);
                osc2.frequency.exponentialRampToValueAtTime(825, now + 0.28);
                osc2.frequency.setValueAtTime(825, now + 0.75);
                g2.gain.exponentialRampToValueAtTime(0.01, now + 1.2);

                osc1.start(now);
                osc2.start(now);
                osc1.stop(now + 1.25);
                osc2.stop(now + 1.25);
            }
            // 2. HEAT STRESS & NOAA THERMAL HAZARD: Undulating Solar Heatwave Shimmer (Slow Warm Ambient Warble)
            else if (key === 'heat' || key === 'thermal' || key === 'weather') {
                const { osc, gain } = createSynth('sine');
                gain.gain.setValueAtTime(0.01, now);
                gain.gain.linearRampToValueAtTime(0.3, now + 0.08);
                
                for (let i = 0; i < 3; i++) {
                    const t = now + i * 0.38;
                    osc.frequency.setValueAtTime(587.33, t);
                    osc.frequency.exponentialRampToValueAtTime(440.00, t + 0.22);
                    osc.frequency.setValueAtTime(440.00, t + 0.35);
                }
                gain.gain.exponentialRampToValueAtTime(0.01, now + 1.2);
                osc.start(now);
                osc.stop(now + 1.25);
            }
            // 3. MACHINERY & FORKLIFT COLLISION BUFFER: Rapid Reversing Sonar Collision Chirp (Staccato 4-Ping)
            else if (key === 'proximity' || key === 'forklift' || key === 'machinery') {
                const { osc, gain } = createSynth('triangle');
                const pings = [1350, 1500, 1650, 1850];
                gain.gain.setValueAtTime(0, now);
                pings.forEach((freq, idx) => {
                    const t = now + idx * 0.11;
                    osc.frequency.setValueAtTime(freq, t);
                    gain.gain.setValueAtTime(0.35, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.08);
                });
                osc.start(now);
                osc.stop(now + 0.55);
            }
            // 4. FIRE & SMOKE HAZARD: Full European Two-Tone Evacuation Wail (980Hz <-> 650Hz Alternating)
            else if (key === 'fire' || key === 'smoke') {
                const { osc, gain } = createSynth('sawtooth');
                gain.gain.setValueAtTime(0.28, now);
                for (let i = 0; i < 4; i++) {
                    const t = now + i * 0.36;
                    osc.frequency.setValueAtTime(980, t);
                    osc.frequency.setValueAtTime(650, t + 0.18);
                }
                gain.gain.exponentialRampToValueAtTime(0.01, now + 1.55);
                osc.start(now);
                osc.stop(now + 1.6);
            }
            // 5. WORKER FALL & MAN-DOWN EMERGENCY: Descending Medical Distress Code Glide (920Hz -> 240Hz + Heart-Thump)
            else if (key === 'fall' || key === 'collapse') {
                const { osc, gain } = createSynth('triangle');
                gain.gain.setValueAtTime(0.35, now);
                osc.frequency.setValueAtTime(920, now);
                osc.frequency.exponentialRampToValueAtTime(240, now + 0.85);
                gain.gain.exponentialRampToValueAtTime(0.05, now + 0.88);
                
                gain.gain.setValueAtTime(0.35, now + 0.95);
                osc.frequency.setValueAtTime(160, now + 0.95);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 1.08);
                gain.gain.setValueAtTime(0.3, now + 1.15);
                osc.frequency.setValueAtTime(140, now + 1.15);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 1.35);
                osc.start(now);
                osc.stop(now + 1.4);
            }
            // 6. HEIGHT SAFETY & FULL-BODY HARNESS: High-Altitude Emergency Whistle Flutter (1760Hz Vibrato Burst)
            else if (key === 'harness' || key === 'height') {
                const { osc, gain } = createSynth('square');
                gain.gain.setValueAtTime(0, now);
                for (let b = 0; b < 3; b++) {
                    const t = now + b * 0.15;
                    osc.frequency.setValueAtTime(1650 + (b * 90), t);
                    gain.gain.setValueAtTime(0.22, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.11);
                }
                osc.start(now);
                osc.stop(now + 0.55);
            }
            // 7. CRANE SUSPENDED LOAD DROP ZONE: Sub-Bass Overhead Foghorn Rumble (Heavy 220Hz -> 310Hz Sawtooth)
            else if (key === 'crane' || key === 'suspended_load' || key === 'suspended') {
                const { osc, gain } = createSynth('sawtooth');
                gain.gain.setValueAtTime(0.01, now);
                gain.gain.linearRampToValueAtTime(0.38, now + 0.08);
                osc.frequency.setValueAtTime(220, now);
                osc.frequency.linearRampToValueAtTime(310, now + 0.4);
                osc.frequency.setValueAtTime(310, now + 0.65);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.85);
                osc.start(now);
                osc.stop(now + 0.9);
            }
            // 8. VIRTUAL DANGER ZONE GEOFENCE: Laser Perimeter Tripwire Zaps (1250Hz -> 750Hz Rapid Zaps)
            else if (key === 'geofence' || key === 'perimeter') {
                const { osc, gain } = createSynth('square');
                gain.gain.setValueAtTime(0, now);
                for (let i = 0; i < 3; i++) {
                    const t = now + i * 0.16;
                    osc.frequency.setValueAtTime(1300, t);
                    osc.frequency.exponentialRampToValueAtTime(750, t + 0.11);
                    gain.gain.setValueAtTime(0.26, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.12);
                }
                osc.start(now);
                osc.stop(now + 0.55);
            }
            // 9. TACTICAL NIGHT SHIFT PERIMETER GUARD: High-Speed Police Strobe Siren (1100Hz <-> 1600Hz Strobe)
            else if (key === 'night' || key === 'night_intrusion' || key === 'intrusion') {
                const { osc, gain } = createSynth('sawtooth');
                gain.gain.setValueAtTime(0.28, now);
                for (let i = 0; i < 5; i++) {
                    const t = now + i * 0.16;
                    osc.frequency.setValueAtTime(i % 2 === 0 ? 1550 : 1100, t);
                }
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.9);
                osc.start(now);
                osc.stop(now + 0.95);
            }
            // 10. CONFINED SPACE HEADCOUNT & STAY-TIMER: Hollow Subterranean 3-Bell Toll (392Hz -> 330Hz -> 261Hz)
            else if (key === 'confined' || key === 'confined_space') {
                const { osc, gain } = createSynth('sine');
                const bells = [392.00, 329.63, 261.63];
                gain.gain.setValueAtTime(0, now);
                bells.forEach((freq, idx) => {
                    const t = now + idx * 0.28;
                    osc.frequency.setValueAtTime(freq, t);
                    gain.gain.setValueAtTime(0.35, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.24);
                });
                osc.start(now);
                osc.stop(now + 0.95);
            }
            // 11. HOT WORK & FIRE EXTINGUISHER PROXIMITY: Electric Arc Spark Crackle (Rapid 1600Hz / 800Hz Toggling)
            else if (key === 'welding' || key === 'hot_work') {
                const { osc, gain } = createSynth('sawtooth');
                gain.gain.setValueAtTime(0.26, now);
                for (let i = 0; i < 8; i++) {
                    const t = now + i * 0.07;
                    osc.frequency.setValueAtTime(i % 2 === 0 ? 1600 : 800, t);
                }
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.65);
                osc.start(now);
                osc.stop(now + 0.7);
            }
            // 12. TRENCH EXCAVATION MARGIN: Sub-Bass Earth Cave-in Grind Rumble (180Hz Heavy Low Sawtooth)
            else if (key === 'trench' || key === 'trench_margin') {
                const { osc, gain } = createSynth('sawtooth');
                gain.gain.setValueAtTime(0.01, now);
                gain.gain.linearRampToValueAtTime(0.4, now + 0.08);
                osc.frequency.setValueAtTime(175, now);
                osc.frequency.linearRampToValueAtTime(195, now + 0.35);
                osc.frequency.linearRampToValueAtTime(155, now + 0.7);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.85);
                osc.start(now);
                osc.stop(now + 0.9);
            }
            // 13. HARDHAT / SAFETY HELMET: Bright Upward Safety Chirp (650Hz -> 1250Hz Rising Sine)
            else if (key === 'helmet' || key === 'ppe_helmet') {
                const { osc, gain } = createSynth('sine');
                gain.gain.setValueAtTime(0.01, now);
                gain.gain.linearRampToValueAtTime(0.3, now + 0.05);
                osc.frequency.setValueAtTime(650, now);
                osc.frequency.exponentialRampToValueAtTime(1250, now + 0.35);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.48);
                osc.start(now);
                osc.stop(now + 0.5);
            }
            // 14. HIGH-VISIBILITY SAFETY VEST: Musical Tri-Tone Harmonic Chord (C5: 523Hz -> E5: 659Hz -> G5: 784Hz)
            else if (key === 'vest' || key === 'ppe_vest') {
                const { osc, gain } = createSynth('triangle');
                gain.gain.setValueAtTime(0, now);
                const notes = [523.25, 659.25, 783.99];
                notes.forEach((freq, idx) => {
                    const t = now + idx * 0.12;
                    osc.frequency.setValueAtTime(freq, t);
                    gain.gain.setValueAtTime(0.3, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.18);
                });
                osc.start(now);
                osc.stop(now + 0.55);
            }
            // 15. CELLPHONE DISTRACTION: Digital Mobile Notification Double-Ding (1760Hz -> 2093Hz Pure Sine)
            else if (key === 'phone') {
                const { osc, gain } = createSynth('sine');
                gain.gain.setValueAtTime(0, now);
                osc.frequency.setValueAtTime(1760, now);
                gain.gain.setValueAtTime(0.28, now);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.09);
                
                osc.frequency.setValueAtTime(2093, now + 0.12);
                gain.gain.setValueAtTime(0.3, now + 0.12);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
                
                osc.start(now);
                osc.stop(now + 0.4);
            }
            // 16. SMART TURNSTILE GATE PASS: Harmonious Ascending Arpeggio (C5 -> E5 -> G5 -> C6)
            else if (key === 'gate_pass') {
                const { osc, gain } = createSynth('sine');
                const chords = [523.25, 659.25, 783.99, 1046.50];
                gain.gain.setValueAtTime(0, now);
                chords.forEach((freq, idx) => {
                    const t = now + idx * 0.11;
                    osc.frequency.setValueAtTime(freq, t);
                    gain.gain.setValueAtTime(0.25, t);
                    gain.gain.exponentialRampToValueAtTime(0.01, t + 0.14);
                });
                osc.start(now);
                osc.stop(now + 0.6);
            }
            // 17. SMART TURNSTILE GATE FAIL: Harsh Low Rejection Double Buzz (330Hz -> 165Hz Sawtooth)
            else if (key === 'gate_fail' || key === 'gate_denied') {
                const { osc, gain } = createSynth('sawtooth');
                gain.gain.setValueAtTime(0.35, now);
                osc.frequency.setValueAtTime(330, now);
                osc.frequency.exponentialRampToValueAtTime(165, now + 0.18);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.2);

                gain.gain.setValueAtTime(0.35, now + 0.26);
                osc.frequency.setValueAtTime(220, now + 0.26);
                osc.frequency.exponentialRampToValueAtTime(140, now + 0.52);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.58);

                osc.start(now);
                osc.stop(now + 0.62);
            }
            // 18. AUTOPILOT AWAY MODE: System Active Confirmation Chime (880Hz -> 1320Hz)
            else if (key === 'autopilot') {
                const { osc, gain } = createSynth('triangle');
                gain.gain.setValueAtTime(0.25, now);
                osc.frequency.setValueAtTime(880, now);
                gain.gain.setValueAtTime(0.28, now + 0.1);
                osc.frequency.setValueAtTime(1320, now + 0.1);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.4);
                osc.start(now);
                osc.stop(now + 0.45);
            }
            // Fallback: Clean Industrial Tone
            else {
                const { osc, gain } = createSynth('sine');
                gain.gain.setValueAtTime(0.2, now);
                osc.frequency.setValueAtTime(660, now);
                gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
                osc.start(now);
                osc.stop(now + 0.4);
            }
        } catch (e) {
            console.warn('[AudioSynth Error]', e);
        }
    }
    window.playClientAcousticTone = playClientAcousticTone;

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

    // ================= 25. Industrial Zone & Multi-Camera CCTV Grid =================
    // (currentZoneBadge already declared at top)
    const navZoneText = document.getElementById('navZoneText');
    const zoneTabsList = document.getElementById('zoneTabsList');
    const btnViewGrid = document.getElementById('btnViewGrid');
    const btnViewFocus = document.getElementById('btnViewFocus');
    const btnOpenZoneModal = document.getElementById('btnOpenZoneModal');
    const cctvGridLayout = document.getElementById('cctvGridLayout');
    const cctvSingleLayout = document.getElementById('cctvSingleLayout');
    const cctvThumbnailStrip = document.getElementById('cctvThumbnailStrip');

    // Modal elements
    const zoneCameraModal = document.getElementById('zoneCameraModal');
    const btnCloseZoneModal = document.getElementById('btnCloseZoneModal');
    const btnCloseZoneFooter = document.getElementById('btnCloseZoneFooter');
    const modalZoneSelect = document.getElementById('modalZoneSelect');
    const btnModalAddZone = document.getElementById('btnModalAddZone');
    const btnModalDeleteZone = document.getElementById('btnModalDeleteZone');
    const newZoneFormBox = document.getElementById('newZoneFormBox');
    const newZoneNameInput = document.getElementById('newZoneNameInput');
    const newZoneDescInput = document.getElementById('newZoneDescInput');
    const btnSubmitNewZone = document.getElementById('btnSubmitNewZone');
    const btnCancelNewZone = document.getElementById('btnCancelNewZone');
    const lblActiveZoneName = document.getElementById('lblActiveZoneName');
    const btnModalAddCamera = document.getElementById('btnModalAddCamera');
    const newCameraFormBox = document.getElementById('newCameraFormBox');
    const newCamNameInput = document.getElementById('newCamNameInput');
    const newCamSourceInput = document.getElementById('newCamSourceInput');
    const newCamFocusInput = document.getElementById('newCamFocusInput');
    const btnSubmitNewCam = document.getElementById('btnSubmitNewCam');
    const btnCancelNewCam = document.getElementById('btnCancelNewCam');
    const modalCameraList = document.getElementById('modalCameraList');

    let isMultiGridMode = true; // Default: Multi-Grid view
    let activeZoneData = null;
    let cachedCameras = [];

    async function loadZonesAndCameras() {
        try {
            const res = await fetch('/api/zones');
            if (!res.ok) return;
            const data = await res.json();
            const zones = data.zones || [];
            const activeId = data.active_zone_id || 'zone_1';

            // 1. Update Header text
            if (navZoneText) {
                navZoneText.innerText = data.active_zone_name || 'Zone 1 - Main Floor';
            }
            if (lblActiveZoneName) {
                lblActiveZoneName.innerText = data.active_zone_name || 'Zone 1';
            }

            // 2. Render Zone Tabs Pills (In-place active toggle to avoid DOM thrashing)
            if (zoneTabsList) {
                const existingPills = Array.from(zoneTabsList.querySelectorAll('.zone-pill'));
                const existingPillIds = existingPills.map(p => p.getAttribute('data-zone'));
                const newZoneIds = zones.map(z => z.id);
                const pillsMatch = existingPillIds.length === newZoneIds.length && existingPillIds.every((id, i) => id === newZoneIds[i]);

                if (pillsMatch) {
                    existingPills.forEach(p => {
                        const zid = p.getAttribute('data-zone');
                        if (zid === activeId) {
                            p.classList.add('active');
                        } else {
                            p.classList.remove('active');
                        }
                    });
                } else {
                    zoneTabsList.innerHTML = '';
                    zones.forEach(z => {
                        const pill = document.createElement('button');
                        pill.type = 'button';
                        pill.className = `zone-pill ${z.id === activeId ? 'active' : ''}`;
                        pill.setAttribute('data-zone', z.id);
                        pill.innerHTML = `
                            <span class="pill-dot"></span> 📍 ${escapeHtml(z.name)} 
                            <span class="cam-count-tag">${(z.cameras || []).length} Cams</span>
                        `;
                        pill.addEventListener('click', () => switchZone(z.id));
                        zoneTabsList.appendChild(pill);
                    });

                    // Re-add "+ Add Zone" pill
                    const addPill = document.createElement('button');
                    addPill.type = 'button';
                    addPill.className = 'btn-add-zone-pill';
                    addPill.id = 'btnQuickAddZone';
                    addPill.innerHTML = '➕ Add Zone';
                    addPill.addEventListener('click', () => {
                        openZoneModal();
                        if (newZoneFormBox) newZoneFormBox.style.display = 'block';
                    });
                    zoneTabsList.appendChild(addPill);
                }
            }

            // 3. Render Modal Zone Select
            if (modalZoneSelect) {
                modalZoneSelect.innerHTML = '';
                zones.forEach(z => {
                    const opt = document.createElement('option');
                    opt.value = z.id;
                    opt.innerText = z.name;
                    if (z.id === activeId) opt.selected = true;
                    modalZoneSelect.appendChild(opt);
                });
            }

            // 4. Fetch and render cameras for active zone
            await refreshActiveZoneCameras();

        } catch (e) {
            console.warn('[Zone Manager] Error loading zones:', e);
        }
    }

    async function refreshActiveZoneCameras() {
        try {
            const res = await fetch('/api/zone/cameras');
            if (!res.ok) return;
            const data = await res.json();
            activeZoneData = data.active_zone || {};
            cachedCameras = data.cameras || [];
            const focusedId = data.focused_cam_id || (cachedCameras[0] ? cachedCameras[0].id : null);

            renderCCTVGrid(cachedCameras);
            renderCCTVThumbnails(cachedCameras, focusedId);
            renderModalCameraList(cachedCameras);
        } catch (e) {
            console.warn('[Zone Manager] Error refreshing cameras:', e);
        }
    }

    function renderCCTVGrid(cameras) {
        if (!cctvGridLayout) return;

        if (!cameras || cameras.length === 0) {
            cctvGridLayout.innerHTML = `
                <div style="grid-column: 1 / -1; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #94A3B8;">
                    <p style="font-size: 1.1rem; margin-bottom: 8px;">📷 No cameras configured for this zone yet.</p>
                    <button class="btn btn-sm btn-accent" id="btnEmptyAddCam">➕ Add Camera Now</button>
                </div>
            `;
            const emptyBtn = document.getElementById('btnEmptyAddCam');
            if (emptyBtn) emptyBtn.addEventListener('click', () => openZoneModal(true));
            return;
        }

        // Optimization: In-place DOM update when camera list structure has not changed
        const existingCards = Array.from(cctvGridLayout.querySelectorAll('.cctv-card'));
        const existingIds = existingCards.map(c => c.getAttribute('data-cam-id'));
        const targetIds = cameras.map(c => c.id);
        const structureMatches = existingIds.length === targetIds.length && existingIds.every((id, idx) => id === targetIds[idx]);

        if (structureMatches) {
            cameras.forEach((cam, idx) => {
                const card = existingCards[idx];
                const hasHazard = !!(cam.stats && (cam.stats.fire_detected || (cam.stats.active_violations && cam.stats.active_violations.length > 0)));
                if (hasHazard && !card.classList.contains('has-hazard')) {
                    card.classList.add('has-hazard');
                } else if (!hasHazard && card.classList.contains('has-hazard')) {
                    card.classList.remove('has-hazard');
                }

                const workersCount = cam.stats ? (cam.stats.total_workers || 0) : 0;
                const compRate = cam.stats ? (cam.stats.compliance_rate || 100) : 100;
                const compColor = compRate >= 80 ? '#10B981' : compRate >= 50 ? '#F59E0B' : '#EF4444';

                const statsEl = card.querySelector('.cctv-card-stats');
                if (statsEl) {
                    statsEl.style.color = compColor;
                    statsEl.textContent = `👷 ${workersCount} (${compRate}%)`;
                }
            });
            return;
        }

        // Structural rebuild only on camera add/delete or zone switch
        cctvGridLayout.innerHTML = '';

        // Adjust grid template columns based on camera count (e.g. 1, 2, 4, 6)
        if (cameras.length <= 1) {
            cctvGridLayout.style.gridTemplateColumns = '1fr';
            cctvGridLayout.style.gridTemplateRows = '1fr';
        } else if (cameras.length <= 4) {
            cctvGridLayout.style.gridTemplateColumns = 'repeat(2, 1fr)';
            cctvGridLayout.style.gridTemplateRows = 'repeat(2, 1fr)';
        } else {
            cctvGridLayout.style.gridTemplateColumns = 'repeat(3, 1fr)';
            cctvGridLayout.style.gridTemplateRows = 'repeat(2, 1fr)';
        }

        cameras.forEach(cam => {
            const card = document.createElement('div');
            card.className = `cctv-card ${cam.stats && (cam.stats.fire_detected || (cam.stats.active_violations && cam.stats.active_violations.length > 0)) ? 'has-hazard' : ''}`;
            card.setAttribute('data-cam-id', cam.id);
            card.title = `Click to zoom into ${cam.name}`;

            const workersCount = cam.stats ? (cam.stats.total_workers || 0) : 0;
            const compRate = cam.stats ? (cam.stats.compliance_rate || 100) : 100;
            const compColor = compRate >= 80 ? '#10B981' : compRate >= 50 ? '#F59E0B' : '#EF4444';

            card.innerHTML = `
                <div class="cctv-card-header">
                    <span class="cctv-card-title">📹 ${escapeHtml(cam.name)}</span>
                    <span class="cctv-live-tag">● LIVE</span>
                </div>
                <div class="cctv-card-media">
                    <img src="/api/stream/${encodeURIComponent(cam.id)}" class="cctv-card-img" alt="${escapeHtml(cam.name)}" loading="lazy">
                </div>
                <div class="cctv-card-footer">
                    <span class="cctv-focus-tag">${escapeHtml(cam.focus || 'Safety')}</span>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <span class="cctv-card-stats" style="color: ${compColor}; font-weight: 700;">👷 ${workersCount} (${compRate}%)</span>
                        <span class="cctv-btn-expand">⛶ Focus</span>
                    </div>
                </div>
            `;

            card.addEventListener('click', () => {
                focusOnCamera(cam.id);
            });

            cctvGridLayout.appendChild(card);
        });
    }

    function renderCCTVThumbnails(cameras, focusedId) {
        if (!cctvThumbnailStrip) return;

        // Optimization: In-place highlight toggle to avoid recreating thumbnail <img> elements
        const existingThumbs = Array.from(cctvThumbnailStrip.querySelectorAll('.cctv-thumb-card'));
        const existingIds = existingThumbs.map(t => t.getAttribute('data-cam-id'));
        const targetIds = (cameras || []).map(c => c.id);
        const structureMatches = existingIds.length === targetIds.length && existingIds.every((id, idx) => id === targetIds[idx]);

        if (structureMatches) {
            existingThumbs.forEach(t => {
                const cid = t.getAttribute('data-cam-id');
                if (cid === focusedId) {
                    t.classList.add('active-thumb');
                } else {
                    t.classList.remove('active-thumb');
                }
            });
            return;
        }

        cctvThumbnailStrip.innerHTML = '';

        cameras.forEach(cam => {
            const thumb = document.createElement('div');
            thumb.className = `cctv-thumb-card ${cam.id === focusedId ? 'active-thumb' : ''}`;
            thumb.setAttribute('data-cam-id', cam.id);
            thumb.title = `Switch focus to ${cam.name}`;
            thumb.innerHTML = `
                <img src="/api/snapshot/${encodeURIComponent(cam.id)}" alt="${escapeHtml(cam.name)}" loading="lazy">
                <span class="cctv-thumb-title">${escapeHtml(cam.name)}</span>
            `;
            thumb.addEventListener('click', (e) => {
                e.stopPropagation();
                focusOnCamera(cam.id);
            });
            cctvThumbnailStrip.appendChild(thumb);
        });
    }

    function renderModalCameraList(cameras) {
        if (!modalCameraList) return;
        modalCameraList.innerHTML = '';

        if (!cameras || cameras.length === 0) {
            modalCameraList.innerHTML = `<p style="color: #94A3B8; font-size: 0.85rem;">No cameras configured in this zone yet. Click "Add Camera to Zone" above.</p>`;
            return;
        }

        cameras.forEach(cam => {
            const card = document.createElement('div');
            card.className = 'modal-cam-card';
            card.innerHTML = `
                <div class="modal-cam-header">
                    <span class="modal-cam-name">📹 ${escapeHtml(cam.name)}</span>
                    <button type="button" class="btn btn-sm btn-outline btn-delete-cam" style="border-color: #EF4444; color: #EF4444; padding: 2px 7px; font-size: 0.7rem;" data-cam-id="${cam.id}" title="Remove Camera">🗑️</button>
                </div>
                <div class="modal-cam-source"><b>Source:</b> <code>${escapeHtml(String(cam.source))}</code></div>
                <div class="modal-cam-focus">🎯 <b>Focus:</b> ${escapeHtml(cam.focus)}</div>
            `;

            const delBtn = card.querySelector('.btn-delete-cam');
            if (delBtn) {
                delBtn.addEventListener('click', async () => {
                    if (confirm(`Remove camera "${cam.name}" from this zone?`)) {
                        await deleteCamera(cam.id);
                    }
                });
            }

            modalCameraList.appendChild(card);
        });
    }

    async function switchZone(zoneId) {
        try {
            // 1. Optimistic UI update: highlight selected zone pill immediately
            if (zoneTabsList) {
                zoneTabsList.querySelectorAll('.zone-pill').forEach(p => {
                    if (p.getAttribute('data-zone') === zoneId) {
                        p.classList.add('active');
                    } else {
                        p.classList.remove('active');
                    }
                });
            }

            // 2. Disconnect previous camera video feeds so browser immediately frees HTTP sockets
            if (cctvGridLayout) {
                cctvGridLayout.querySelectorAll('.cctv-card-img').forEach(img => {
                    img.src = '';
                });
            }

            // 3. Post zone switch to backend
            const formData = new FormData();
            formData.append('zone_id', zoneId);
            const res = await fetch('/api/zones/active', { method: 'POST', body: formData });
            if (res.ok) {
                const resData = await res.json();
                if (resData.cameras && resData.active_zone) {
                    // Fast path: Update directly from single response without extra fetch round-trips
                    activeZoneData = resData.active_zone;
                    cachedCameras = resData.cameras;
                    const focusedId = resData.focused_cam_id || (cachedCameras[0] ? cachedCameras[0].id : null);
                    
                    if (navZoneText) navZoneText.innerText = activeZoneData.name || 'Zone';
                    if (lblActiveZoneName) lblActiveZoneName.innerText = activeZoneData.name || 'Zone';
                    
                    renderCCTVGrid(cachedCameras);
                    renderCCTVThumbnails(cachedCameras, focusedId);
                    renderModalCameraList(cachedCameras);
                } else {
                    await loadZonesAndCameras();
                }
            }
        } catch (e) {
            console.error('[Zone Switch Error]', e);
        }
    }

    let activeFocusedCamId = null;

    async function focusOnCamera(camId) {
        try {
            activeFocusedCamId = camId;
            const formData = new FormData();
            formData.append('cam_id', camId);
            await fetch('/api/zone/camera/focus', { method: 'POST', body: formData });
            
            // Switch to single view
            setViewMode(false);
            
            // Highlight thumbnail
            document.querySelectorAll('.cctv-thumb-card').forEach(t => {
                const cid = t.getAttribute('data-cam-id');
                if (cid === camId) {
                    t.classList.add('active-thumb');
                } else {
                    t.classList.remove('active-thumb');
                }
            });

            // Update single video feed player
            const liveVideoFeed = document.getElementById('liveVideoFeed');
            if (liveVideoFeed) {
                liveVideoFeed.src = `/api/stream/${encodeURIComponent(camId)}`;
            }
        } catch (e) {
            console.error('[Camera Focus Error]', e);
        }
    }

    function setViewMode(gridMode) {
        isMultiGridMode = gridMode;
        const liveVideoFeed = document.getElementById('liveVideoFeed');

        if (isMultiGridMode) {
            if (cctvGridLayout) cctvGridLayout.style.display = 'grid';
            if (cctvSingleLayout) cctvSingleLayout.style.display = 'none';
            if (btnViewGrid) btnViewGrid.classList.add('active');
            if (btnViewFocus) btnViewFocus.classList.remove('active');

            // Free socket by disconnecting hidden single video feed
            if (liveVideoFeed) {
                liveVideoFeed.src = "";
            }

            // Restore stream src for visible grid cards
            if (cctvGridLayout) {
                cctvGridLayout.querySelectorAll('.cctv-card').forEach(card => {
                    const cid = card.getAttribute('data-cam-id');
                    const img = card.querySelector('.cctv-card-img');
                    if (img && cid && (!img.src || img.src === window.location.href || img.src.endsWith('/'))) {
                        img.src = `/api/stream/${encodeURIComponent(cid)}`;
                    }
                });
            }
        } else {
            if (cctvGridLayout) cctvGridLayout.style.display = 'none';
            if (cctvSingleLayout) cctvSingleLayout.style.display = 'flex';
            if (btnViewGrid) btnViewGrid.classList.remove('active');
            if (btnViewFocus) btnViewFocus.classList.add('active');

            // Free 4 sockets by pausing hidden grid streams
            if (cctvGridLayout) {
                cctvGridLayout.querySelectorAll('.cctv-card-img').forEach(img => {
                    img.src = "";
                });
            }

            // Connect only the focused single camera
            if (liveVideoFeed) {
                const targetId = activeFocusedCamId || (cachedCameras[0] ? cachedCameras[0].id : 'cam_01');
                liveVideoFeed.src = `/api/stream/${encodeURIComponent(targetId)}`;
            }
        }
    }

    function openZoneModal(openAddCam = false) {
        if (zoneCameraModal) {
            zoneCameraModal.style.display = 'flex';
            if (newZoneFormBox) newZoneFormBox.style.display = 'none';
            if (newCameraFormBox) newCameraFormBox.style.display = openAddCam ? 'block' : 'none';
        }
    }

    function closeZoneModal() {
        if (zoneCameraModal) {
            zoneCameraModal.style.display = 'none';
        }
    }

    async function deleteCamera(camId) {
        if (!activeZoneData || !activeZoneData.id) return;
        try {
            const formData = new FormData();
            formData.append('cam_id', camId);
            const res = await fetch(`/api/zones/${encodeURIComponent(activeZoneData.id)}/cameras/delete`, { method: 'POST', body: formData });
            if (res.ok) {
                await refreshActiveZoneCameras();
            }
        } catch (e) {
            console.error('[Delete Camera Error]', e);
        }
    }

    // Modal Events Binding
    if (currentZoneBadge) currentZoneBadge.addEventListener('click', () => openZoneModal());
    if (btnOpenZoneModal) btnOpenZoneModal.addEventListener('click', () => openZoneModal());
    if (btnCloseZoneModal) btnCloseZoneModal.addEventListener('click', closeZoneModal);
    if (btnCloseZoneFooter) btnCloseZoneFooter.addEventListener('click', closeZoneModal);

    if (btnViewGrid) btnViewGrid.addEventListener('click', () => setViewMode(true));
    if (btnViewFocus) btnViewFocus.addEventListener('click', () => setViewMode(false));

    if (modalZoneSelect) {
        modalZoneSelect.addEventListener('change', (e) => {
            switchZone(e.target.value);
        });
    }

    if (btnModalAddZone) {
        btnModalAddZone.addEventListener('click', () => {
            if (newZoneFormBox) {
                newZoneFormBox.style.display = newZoneFormBox.style.display === 'none' ? 'block' : 'none';
            }
        });
    }

    if (btnCancelNewZone) {
        btnCancelNewZone.addEventListener('click', () => {
            if (newZoneFormBox) newZoneFormBox.style.display = 'none';
        });
    }

    if (btnSubmitNewZone) {
        btnSubmitNewZone.addEventListener('click', async () => {
            const name = newZoneNameInput.value.trim();
            const desc = newZoneDescInput.value.trim();
            if (!name) {
                alert('Please enter a Zone Name');
                return;
            }
            try {
                const formData = new FormData();
                formData.append('name', name);
                formData.append('description', desc);
                const res = await fetch('/api/zones/add', { method: 'POST', body: formData });
                if (res.ok) {
                    newZoneNameInput.value = '';
                    newZoneDescInput.value = '';
                    if (newZoneFormBox) newZoneFormBox.style.display = 'none';
                    await loadZonesAndCameras();
                }
            } catch (e) {
                console.error('[Add Zone Error]', e);
            }
        });
    }

    if (btnModalDeleteZone) {
        btnModalDeleteZone.addEventListener('click', async () => {
            if (!activeZoneData || !activeZoneData.id) return;
            if (confirm(`Are you sure you want to delete zone "${activeZoneData.name}"?`)) {
                try {
                    const formData = new FormData();
                    formData.append('zone_id', activeZoneData.id);
                    const res = await fetch('/api/zones/delete', { method: 'POST', body: formData });
                    if (res.ok) {
                        await loadZonesAndCameras();
                    } else {
                        alert('Cannot delete the only remaining zone.');
                    }
                } catch (e) {
                    console.error('[Delete Zone Error]', e);
                }
            }
        });
    }

    if (btnModalAddCamera) {
        btnModalAddCamera.addEventListener('click', () => {
            if (newCameraFormBox) {
                newCameraFormBox.style.display = newCameraFormBox.style.display === 'none' ? 'block' : 'none';
            }
        });
    }

    if (btnCancelNewCam) {
        btnCancelNewCam.addEventListener('click', () => {
            if (newCameraFormBox) newCameraFormBox.style.display = 'none';
        });
    }

    if (btnSubmitNewCam) {
        btnSubmitNewCam.addEventListener('click', async () => {
            const name = newCamNameInput.value.trim();
            const source = newCamSourceInput.value.trim();
            const focus = newCamFocusInput.value.trim();
            if (!name || !source) {
                alert('Please enter both Camera Name and Video Source');
                return;
            }
            if (!activeZoneData || !activeZoneData.id) return;

            try {
                const formData = new FormData();
                formData.append('name', name);
                formData.append('source', source);
                formData.append('focus', focus || 'General Safety');
                const isNum = !isNaN(source);
                formData.append('cam_type', source.startsWith('http') || source.startsWith('rtsp') ? 'rtsp' : isNum ? 'webcam' : 'industrial_feed');

                const res = await fetch(`/api/zones/${encodeURIComponent(activeZoneData.id)}/cameras/add`, { method: 'POST', body: formData });
                if (res.ok) {
                    newCamNameInput.value = '';
                    newCamSourceInput.value = '';
                    newCamFocusInput.value = '';
                    if (newCameraFormBox) newCameraFormBox.style.display = 'none';
                    await refreshActiveZoneCameras();
                }
            } catch (e) {
                console.error('[Add Camera Error]', e);
            }
        });
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // Initial load
    loadZonesAndCameras();

    // Periodic camera stats refresh every 4 seconds to update worker counts & violation tags
    setInterval(() => {
        if (isDocumentVisible && isMultiGridMode && cachedCameras.length > 0) {
            refreshActiveZoneCameras();
        }
    }, 4000);
});



