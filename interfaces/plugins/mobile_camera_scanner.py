import socket
from typing import Dict, Any, Optional, Tuple
from interfaces.plugins.base import BaseWebPlugin
from interfaces.plugins.qr_generator import PureQRCode

def get_local_ip() -> str:
    """Detect the local primary network IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class MobileCameraScannerPlugin(BaseWebPlugin):
    """
    Modular plugin for smartphone camera barcode scanning, automatic warranty lookup,
    and direct label printing with QR code pairing for desktop-to-mobile setup.
    """

    @property
    def plugin_id(self) -> str:
        return "mobile_camera_scanner"

    @property
    def name(self) -> str:
        return "Phone Camera Scanner"

    @property
    def icon(self) -> str:
        return "📱"

    def get_css(self) -> str:
        return """
        .mobile-scanner-card {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 20px;
        }
        .mobile-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }
        .pairing-box {
            background: rgba(56, 189, 248, 0.08);
            border: 1px dashed var(--accent);
            border-radius: 10px;
            padding: 14px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            flex-wrap: wrap;
        }
        .qr-box {
            background: #ffffff;
            padding: 8px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: 120px;
            min-height: 120px;
        }
        .viewfinder-container {
            position: relative;
            width: 100%;
            max-width: 640px;
            margin: 0 auto 16px auto;
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            aspect-ratio: 4 / 3;
            border: 2px solid var(--border);
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        #mobileCameraVideo {
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
        }
        .reticle-box {
            position: absolute;
            top: 20%;
            left: 15%;
            width: 70%;
            height: 60%;
            border: 1px dashed rgba(56, 189, 248, 0.5);
            pointer-events: none;
            box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.45);
            transition: border-color 0.2s;
        }
        .reticle-box.scan-success {
            border: 3px solid var(--success) !important;
            box-shadow: 0 0 0 9999px rgba(34, 197, 94, 0.2) !important;
        }
        .reticle-corner {
            position: absolute;
            width: 16px;
            height: 16px;
            border-color: var(--accent);
            border-style: solid;
        }
        .reticle-corner.top-left { top: -2px; left: -2px; border-width: 3px 0 0 3px; }
        .reticle-corner.top-right { top: -2px; right: -2px; border-width: 3px 3px 0 0; }
        .reticle-corner.bottom-left { bottom: -2px; left: -2px; border-width: 0 0 3px 3px; }
        .reticle-corner.bottom-right { bottom: -2px; right: -2px; border-width: 0 3px 3px 0; }

        .scan-laser {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: #ef4444;
            box-shadow: 0 0 8px #ef4444;
            animation: laserScan 2s infinite ease-in-out;
        }
        @keyframes laserScan {
            0% { top: 0%; opacity: 0.8; }
            50% { top: 98%; opacity: 1; }
            100% { top: 0%; opacity: 0.8; }
        }

        .overlay-msg {
            position: absolute;
            bottom: 12px;
            left: 0;
            right: 0;
            text-align: center;
            background: rgba(15, 23, 42, 0.85);
            color: #fff;
            font-size: 0.85rem;
            padding: 6px 12px;
            backdrop-filter: blur(4px);
        }

        .camera-controls {
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        .scanner-settings {
            background: #090d16;
            padding: 12px 16px;
            border-radius: 8px;
            border: 1px solid var(--border);
            margin-bottom: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .setting-row {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.9rem;
            color: var(--text-main);
            cursor: pointer;
        }
        .result-card {
            margin-top: 16px;
            border-left: 4px solid var(--accent);
            animation: fadeIn 0.25s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }
        """

    def get_content_html(self, host: str, port: int, public_url: Optional[str] = None) -> str:
        local_ip = get_local_ip()
        pairing_url = public_url if public_url else f"http://{local_ip}:{port}"
        qr_svg = PureQRCode(pairing_url).to_svg(120)

        return f"""
        <div class="mobile-scanner-card">
            <div class="mobile-header">
                <h2>📱 Phone Camera Barcode Scanner</h2>
                <span id="cameraStatusBadge" class="badge badge-warning">Camera Standby</span>
            </div>

            <!-- Desktop-to-Mobile Pairing Banner -->
            <div id="desktopPairingBanner" class="pairing-box">
                <div>
                    <div style="font-weight:700; color:var(--accent); font-size:1.05rem;">📲 Open on Your Phone</div>
                    <div style="font-size:0.88rem; color:var(--text-muted); margin-top:4px;">
                        Scan QR code with your phone camera or open:
                        <br>
                        <code id="pairingUrlDisplay" style="color:#fff; font-weight:bold; font-size:1.05rem;">{pairing_url}</code>
                    </div>
                </div>
                <div id="qrCodeContainer" class="qr-box">
                    {qr_svg}
                </div>
            </div>


            <!-- Camera Viewfinder -->
            <div class="viewfinder-container">
                <video id="mobileCameraVideo" playsinline autoplay muted></video>
                <div id="cameraReticle" class="reticle-box">
                    <div class="reticle-corner top-left"></div>
                    <div class="reticle-corner top-right"></div>
                    <div class="reticle-corner bottom-left"></div>
                    <div class="reticle-corner bottom-right"></div>
                    <div class="scan-laser"></div>
                </div>
                <div id="cameraOverlayText" class="overlay-msg">Click 'Start Camera' or open on phone</div>
            </div>

            <!-- Controls -->
            <div class="camera-controls">
                <button id="btnToggleCamera" class="btn btn-primary" onclick="window.mobileScannerPlugin.toggleCamera()">
                    📹 Start Camera
                </button>
                <button id="btnFlipCamera" class="btn btn-secondary" onclick="window.mobileScannerPlugin.flipCamera()" disabled>
                    🔄 Flip Camera
                </button>
                <button id="btnTorch" class="btn btn-outline" onclick="window.mobileScannerPlugin.toggleTorch()" disabled>
                    ⚡ Flashlight
                </button>
            </div>

            <!-- Settings -->
            <div class="scanner-settings">
                <label class="setting-row">
                    <input type="checkbox" id="autoPrintOnScan" checked>
                    <span>⚡ <strong>Auto-Print Label on Scan</strong> (Sends label immediately upon verified lookup)</span>
                </label>
                <label class="setting-row">
                    <input type="checkbox" id="hapticFeedback" checked>
                    <span>🔊 <strong>Audio & Haptic Feedback</strong> (Beep + vibration on successful barcode match)</span>
                </label>
            </div>

            <!-- Result Overlay -->
            <div id="mobileScanResultCard" class="card result-card hidden"></div>
        </div>
        """

    def get_javascript(self) -> str:
        return """
        <script>
        class MobileCameraScannerPluginController {
            constructor() {
                self = this;
                this.stream = null;
                this.facingMode = 'environment';
                this.isScanning = false;
                this.isProcessingScan = false;
                this.lastScannedSerial = '';
                this.lastScanTime = 0;
                this.torchState = false;
                this.barcodeDetector = null;
                this.audioCtx = null;

                document.addEventListener('DOMContentLoaded', () => {
                    this.initBarcodeDetector();

                    // Auto-open camera if launched directly on mobile screen
                    if (window.innerWidth < 768) {
                        const tabBtn = document.getElementById('tab_mobile_camera_scanner');
                        if (tabBtn) tabBtn.click();
                    }
                });
            }


            async initBarcodeDetector() {
                if ('BarcodeDetector' in window) {
                    try {
                        const formats = await BarcodeDetector.getSupportedFormats();
                        this.barcodeDetector = new BarcodeDetector({ formats: formats.length > 0 ? formats : ['code_128', 'code_39', 'qr_code', 'ean_13', 'upc_a'] });
                        console.log('Native BarcodeDetector initialized with formats:', formats);
                    } catch(e) {
                        console.warn('BarcodeDetector format error:', e);
                    }
                }
            }

            async toggleCamera() {
                if (this.isScanning) {
                    this.stopCamera();
                } else {
                    await this.startCamera();
                }
            }

            async startCamera() {
                const video = document.getElementById('mobileCameraVideo');
                const badge = document.getElementById('cameraStatusBadge');
                const overlay = document.getElementById('cameraOverlayText');
                const toggleBtn = document.getElementById('btnToggleCamera');
                const flipBtn = document.getElementById('btnFlipCamera');

                try {
                    overlay.textContent = 'Requesting camera access...';
                    const constraints = {
                        video: {
                            facingMode: { ideal: this.facingMode },
                            width: { ideal: 1280 },
                            height: { ideal: 720 }
                        }
                    };

                    this.stream = await navigator.mediaDevices.getUserMedia(constraints);
                    video.srcObject = this.stream;
                    await video.play();

                    this.isScanning = true;
                    toggleBtn.textContent = '🛑 Stop Camera';
                    toggleBtn.className = 'btn btn-secondary';
                    flipBtn.disabled = false;
                    badge.textContent = 'Camera Active';
                    badge.className = 'badge badge-success';
                    overlay.textContent = 'Point camera at serial barcode...';

                    // Check torch support
                    const track = this.stream.getVideoTracks()[0];
                    const capabilities = track.getCapabilities ? track.getCapabilities() : {};
                    const torchBtn = document.getElementById('btnTorch');
                    if (torchBtn) torchBtn.disabled = !capabilities.torch;

                    this.runScanLoop();
                } catch(err) {
                    console.error('Camera access error:', err);
                    overlay.textContent = 'Camera access error: ' + (err.message || 'Permission denied');
                    badge.textContent = 'Camera Error';
                    badge.className = 'badge badge-danger';
                }
            }

            stopCamera() {
                if (this.stream) {
                    this.stream.getTracks().forEach(track => track.stop());
                    this.stream = null;
                }
                this.isScanning = false;
                const video = document.getElementById('mobileCameraVideo');
                if (video) video.srcObject = null;

                const badge = document.getElementById('cameraStatusBadge');
                const overlay = document.getElementById('cameraOverlayText');
                const toggleBtn = document.getElementById('btnToggleCamera');
                const flipBtn = document.getElementById('btnFlipCamera');
                const torchBtn = document.getElementById('btnTorch');

                if (toggleBtn) {
                    toggleBtn.textContent = '📹 Start Camera';
                    toggleBtn.className = 'btn btn-primary';
                }
                if (flipBtn) flipBtn.disabled = true;
                if (torchBtn) torchBtn.disabled = true;
                if (badge) {
                    badge.textContent = 'Camera Standby';
                    badge.className = 'badge badge-warning';
                }
                if (overlay) overlay.textContent = 'Click \'Start Camera\' to resume scanning';
            }

            async flipCamera() {
                this.facingMode = (this.facingMode === 'environment') ? 'user' : 'environment';
                if (this.isScanning) {
                    this.stopCamera();
                    await this.startCamera();
                }
            }

            async toggleTorch() {
                if (!this.stream) return;
                const track = this.stream.getVideoTracks()[0];
                try {
                    this.torchState = !this.torchState;
                    await track.applyConstraints({ advanced: [{ torch: this.torchState }] });
                    const torchBtn = document.getElementById('btnTorch');
                    if (torchBtn) {
                        torchBtn.className = this.torchState ? 'btn btn-primary' : 'btn btn-outline';
                    }
                } catch(e) {
                    console.warn('Torch toggle failed:', e);
                }
            }

            playBeepSound() {
                if (!document.getElementById('hapticFeedback')?.checked) return;
                try {
                    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);

                    if (!this.audioCtx) {
                        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                    }
                    const osc = this.audioCtx.createOscillator();
                    const gain = this.audioCtx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(880, this.audioCtx.currentTime); // High pitch A5 chime
                    gain.gain.setValueAtTime(0.15, this.audioCtx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + 0.18);
                    osc.connect(gain);
                    gain.connect(this.audioCtx.destination);
                    osc.start();
                    osc.stop(this.audioCtx.currentTime + 0.18);
                } catch(e) {}
            }

            async runScanLoop() {
                const video = document.getElementById('mobileCameraVideo');
                const overlay = document.getElementById('cameraOverlayText');

                while (this.isScanning) {
                    if (video && video.readyState === video.HAVE_ENOUGH_DATA && !this.isProcessingScan) {
                        try {
                            let detectedRawValue = null;
                            if (this.barcodeDetector) {
                                const barcodes = await this.barcodeDetector.detect(video);
                                if (barcodes && barcodes.length > 0) {
                                    detectedRawValue = barcodes[0].rawValue;
                                }
                            }

                            if (detectedRawValue) {
                                const serial = detectedRawValue.trim().toUpperCase();
                                const now = Date.now();
                                // 3 second cooldown for identical barcode
                                if (serial !== this.lastScannedSerial || (now - this.lastScanTime) > 3000) {
                                    this.lastScannedSerial = serial;
                                    this.lastScanTime = now;
                                    await this.handleBarcodeDetected(serial);
                                }
                            }
                        } catch(err) {
                            // frame skip or detection cycle error
                        }
                    }
                    await new Promise(r => setTimeout(r, 120));
                }
            }

            async handleBarcodeDetected(serial) {
                this.isProcessingScan = true;
                this.playBeepSound();

                const reticle = document.getElementById('cameraReticle');
                const overlay = document.getElementById('cameraOverlayText');
                const resultCard = document.getElementById('mobileScanResultCard');
                const autoPrint = document.getElementById('autoPrintOnScan')?.checked ?? true;

                if (reticle) reticle.classList.add('scan-success');
                if (overlay) overlay.textContent = `Barcode Detected: ${serial} — Fetching Warranty...`;

                if (resultCard) {
                    resultCard.classList.remove('hidden');
                    resultCard.innerHTML = `
                        <div style="color:var(--accent); font-size:1.1rem; font-weight:700;">🔍 Scanning Serial: ${serial}</div>
                        <div class="progress-shell"><div class="progress-bar" style="width: 50%;"></div></div>
                        <div style="font-size:0.85rem; color:var(--text-muted);">Verifying live vendor warranty portal...</div>
                    `;
                }

                try {
                    const res = await fetch(`/api/scan?serial=${encodeURIComponent(serial)}&print=${autoPrint}`);
                    const data = await res.json();

                    const statusClass = ['Active', 'Expired', 'Coverage'].includes(String(data.status).split(' ')[0]) ? String(data.status).split(' ')[0] : 'Expired';
                    let printMsg = 'Label: Auto-print off';
                    if (autoPrint && data.print_result) {
                        printMsg = data.print_result.success
                            ? `🖨️ Sent to ${data.print_result.printer || 'Printer'}`
                            : `⚠️ Print Error: ${data.print_result.error || 'Failed'}`;
                    }

                    if (resultCard) {
                        resultCard.innerHTML = `
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <h3 style="margin:0;">${escapeHtml(data.vendor)} - ${escapeHtml(data.model)}</h3>
                                <span class="badge ${statusClass === 'Active' ? 'badge-success' : 'badge-danger'}">${escapeHtml(data.status)}</span>
                            </div>
                            <p style="margin:6px 0 0 0; font-size:1.1rem; font-weight:bold; font-family:monospace; color:var(--accent);">
                                Serial: ${escapeHtml(data.serial)}
                            </p>
                            <p style="margin:4px 0; font-size:0.9rem; color:var(--text-muted);">
                                Coverage Expiration: <strong>${escapeHtml(data.expiration_date)}</strong> (Source: ${escapeHtml(data.source_confidence)})
                            </p>
                            <div style="font-size:0.85rem; font-weight:bold; color:${data.print_result?.success ? 'var(--success)' : 'var(--warning)'}; margin-top:6px;">
                                ${printMsg} (${data.lookup_ms} ms)
                            </div>
                        `;
                    }

                    if (overlay) overlay.textContent = `Verified ${serial} (${data.status}) — Ready for next scan`;
                } catch(err) {
                    if (resultCard) {
                        resultCard.innerHTML = `<div style="color:var(--danger);">Lookup request failed for serial ${serial}</div>`;
                    }
                    if (overlay) overlay.textContent = `Error processing serial ${serial}`;
                } finally {
                    setTimeout(() => {
                        if (reticle) reticle.classList.remove('scan-success');
                        this.isProcessingScan = false;
                    }, 1200);
                }
            }

            handleApiGet(path, queryParams) {
                if (path === '/api/plugins/mobile_camera_scanner/info') {
                    return { local_ip: get_local_ip() };
                }
                return None;
            }
        }
        window.mobileScannerPlugin = new MobileCameraScannerPluginController();
        </script>
        """

    def handle_api_get(self, path: str, query_params: Dict[str, Any]) -> Optional[Tuple[int, Dict[str, Any]]]:
        if path in ("/api/plugins/mobile_camera_scanner/info", "/api/plugins/mobile_camera_scanner/pairing"):
            return 200, {
                "success": True,
                "local_ip": get_local_ip(),
                "plugin_id": self.plugin_id,
            }
        return None
