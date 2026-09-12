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
            
            const live = data.live;
            
            // Compliance Rate
            kpiCompliance.innerText = `${live.compliance_rate}%`;
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
            kpiWorkers.innerText = live.total_workers;
            kpiCompliantWorkers.innerText = live.compliant_workers;

            // Violations
            kpiViolations.innerText = live.violations_count;
            if (live.active_violations.length > 0) {
                kpiViolationDetails.innerText = live.active_violations.join(', ');
            } else {
                kpiViolationDetails.innerText = 'No active violations';
            }

            // Fire / Smoke Hazard Status
            if (live.fire_detected) {
                kpiHazardStatus.innerText = '🔥 FIRE DETECTED!';
                kpiHazardStatus.className = 'kpi-badge badge-danger';
                hazardBanner.style.display = 'flex';
            } else {
                kpiHazardStatus.innerText = 'SAFE';
                kpiHazardStatus.className = 'kpi-badge badge-safe';
                hazardBanner.style.display = 'none';
            }

            // Update Source & Zone
            activeSourceLabel.innerText = `Source: ${data.camera_source}`;
            currentZoneBadge.innerText = `📍 ${data.zone_name}`;
            isMuted = data.is_muted;
            muteStatusText.innerText = isMuted ? 'MUTED' : 'ON';

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
});
