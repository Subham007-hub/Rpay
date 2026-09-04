// State variables
let isListening = false;
let recognition = null;
let pendingHitlProduct = null;

// Initialize Web Speech API Recognition if available
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = function () {
        isListening = true;
        updateOrbState('listening', 'Alexa is listening...');
    };

    recognition.onresult = function (event) {
        const transcript = event.results[0][0].transcript;
        document.getElementById('user-input').value = transcript;
        updateOrbState('idle', `Heard: "${transcript}"`);
        sendChatQuery(transcript);
    };

    recognition.onerror = function (event) {
        console.error('Speech recognition error:', event.error);
        isListening = false;
        if (event.error === 'not-allowed') {
            updateOrbState('idle', '⚠️ Microphone blocked. Allow mic permissions in browser bar.');
        } else {
            updateOrbState('idle', `⚠️ Voice error (${event.error}). Click Orb to retry.`);
        }
    };

    recognition.onend = function () {
        isListening = false;
        if (!window.speechSynthesis.speaking) {
            updateOrbState('idle', 'Click Orb to speak');
        }
    };
}

// Speak text using Web Speech Synthesis
function speakOutLoud(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Stop any previous speech
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;

        utterance.onstart = function () {
            updateOrbState('speaking', 'Alexa is speaking...');
        };

        utterance.onend = function () {
            updateOrbState('idle', 'Click Orb to speak');
        };

        window.speechSynthesis.speak(utterance);
    }
}

// Toggle Mic Listening
function toggleVoiceListening() {
    if (!recognition) {
        alert('Web Speech API is not supported in this browser. Please use text input or Chrome/Edge.');
        return;
    }

    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

// Update Alexa Orb UI State
function updateOrbState(state, statusText) {
    const orb = document.getElementById('alexa-orb');
    const heading = document.getElementById('assistant-status');
    const micBtnText = document.getElementById('mic-text');

    orb.className = `alexa-orb ${state}`;
    if (heading) heading.textContent = statusText;

    if (micBtnText) {
        micBtnText.textContent = state === 'listening' ? 'Listening...' : 'Start Listening';
    }
}

// Tab Switching
function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');

    if (tabId === 'dashboard-tab') {
        loadAuditLogs();
        loadSettings();
    }
}

// Handle Form Submit
function handleFormSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('user-input');
    const query = input.value.trim();
    if (query) {
        sendChatQuery(query);
        input.value = '';
    }
}

// Preset Chips
function runPreset(query) {
    document.getElementById('user-input').value = query;
    sendChatQuery(query);
}

// Send Query to FastAPI Backend
async function sendChatQuery(query, discountOverride = null, humanConfirmed = false) {
    const stream = document.getElementById('conversation-stream');

    // Append User Chat Bubble if new query
    if (!humanConfirmed) {
        const userBubble = document.createElement('div');
        userBubble.className = 'chat-bubble user';
        userBubble.textContent = query;
        stream.appendChild(userBubble);
    }

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                intent: query,
                discount_override: discountOverride,
                human_confirmed: humanConfirmed
            })
        });

        const data = await response.json();

        // Speak Response Aloud
        if (data.speak_text) {
            speakOutLoud(data.speak_text);
        }

        // Render Assistant Response Bubble
        const assistantBubble = document.createElement('div');
        assistantBubble.className = 'chat-bubble assistant';

        let statusBadge = '';
        if (data.status === 'order_created') {
            statusBadge = `<span style="color:#34D399; font-weight:bold;">✅ ORDER CREATED (${data.tier})</span>`;
        } else if (data.status === 'hitl_required') {
            statusBadge = `<span style="color:#FDE047; font-weight:bold;">⚠️ HUMAN CONFIRMATION NEEDED</span>`;
        } else if (data.status === 'declined') {
            statusBadge = `<span style="color:#FCA5A5; font-weight:bold;">⛔ GUARDRAIL DECLINED</span>`;
        }

        let html = `<div>${statusBadge}</div><p style="margin-top:6px;">${data.speak_text}</p>`;

        // Render Product Cards if available
        if (data.products && data.products.length > 0) {
            html += `<div class="product-cards-grid">`;
            data.products.forEach(p => {
                const badgeClass = p.merchant_verified ? 'badge-verified' : 'badge-unverified';
                const badgeText = p.merchant_verified ? 'Verified Seller' : 'Unverified Seller';

                html += `
                    <div class="product-card">
                        <img src="${p.image_url}" class="product-img" alt="${p.name}" onerror="this.onerror=null; this.src='data:image/svg+xml;utf8,<svg xmlns=\'http://www.w3.org/2000/svg\' width=\'400\' height=\'250\' viewBox=\'0 0 400 250\' fill=\'%231E293B\'><rect width=\'400\' height=\'250\' fill=\'%231E293B\'/><text x=\'50%25\' y=\'50%25\' dominant-baseline=\'middle\' text-anchor=\'middle\' fill=\'%2338BDF8\' font-family=\'sans-serif\' font-size=\'20\' font-weight=\'bold\'>📦 ${encodeURIComponent(p.name)}</text></svg>';">
                        <div>
                            <span class="badge ${badgeClass}">${badgeText}</span>
                            <div class="product-title">${p.name}</div>
                            <div class="product-merchant">${p.merchant_name}</div>
                        </div>
                        <div class="product-price">
                            Rs. ${p.price_rupees.toLocaleString()} 
                            <span class="discount-text">(${p.discount_percent}% OFF)</span>
                        </div>
                        <div class="pick-reason">
                            <b>AI Reason:</b> ${p.rank_reason || 'Matched intent'}
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
        }

        // Add Approval Button if Tier 3 HITL required
        if (data.status === 'hitl_required' && data.products.length > 0) {
            const hitlProduct = data.products[0];
            pendingHitlProduct = { query, product: hitlProduct };
            html += `
                <div class="hitl-banner">
                    <span>High-value purchase threshold triggered (> Rs. 5,000).</span>
                    <button class="btn-approve" onclick="openHitlModal()">Review & Approve</button>
                </div>
            `;
        }

        // Add Razorpay Checkout Button if order was created
        if (data.order) {
            const orderAmount = data.order.amount ? (data.order.amount / 100) : (data.products && data.products[0] ? data.products[0].price_rupees : 0);
            const prodName = data.products && data.products[0] ? data.products[0].name : "Selected Product";
            const orderId = data.order.id || "order_demo";
            const payLink = data.order.payment_link || "";

            html += `
                <div style="margin-top:12px; padding:12px; background:rgba(30,41,59,0.7); border-radius:10px; border:1px solid rgba(56,189,248,0.3);">
                    <div style="font-size:12px; color:#94A3B8; margin-bottom:6px;">Razorpay Order ID: <code style="color:#38BDF8;">${orderId}</code></div>
                    <button class="btn-primary" onclick="openPaymentCheckout('${orderId}', ${orderAmount}, '${encodeURIComponent(prodName)}', '${payLink}')" style="display:inline-flex; align-items:center; gap:8px; padding:10px 18px; font-size:14px; font-weight:600; cursor:pointer;">
                        💳 Pay Rs. ${orderAmount.toLocaleString()} via Razorpay
                    </button>
                </div>
            `;
        }

        assistantBubble.innerHTML = html;
        stream.appendChild(assistantBubble);
        stream.scrollTop = stream.scrollHeight;

    } catch (err) {
        console.error('Error processing query:', err);
    }
}

// Interactive Razorpay Checkout Flow
function openPaymentCheckout(orderId, amount, encodedName, payLink) {
    const prodName = decodeURIComponent(encodedName);
    const content = document.getElementById('checkout-body-content');
    content.innerHTML = `
        <div style="text-align:left; font-family:sans-serif;">
            <div style="font-size:13px; color:#64748B;">Order: <span style="font-family:monospace; color:#0F172A; font-weight:bold;">${orderId}</span></div>
            <div style="font-size:18px; font-weight:bold; color:#0F172A; margin:6px 0;">${prodName}</div>
            <div style="font-size:24px; font-weight:800; color:#059669; margin-bottom:16px;">Rs. ${amount.toLocaleString()}</div>
            
            <div style="border-top:1px solid #E2E8F0; padding-top:14px; margin-bottom:16px;">
                <label style="font-size:12px; font-weight:bold; color:#475569; display:block; margin-bottom:8px;">SELECT PAYMENT METHOD</label>
                <div style="display:flex; flex-direction:column; gap:8px;">
                    <label style="display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer; background:#F8FAFC;">
                        <input type="radio" name="pay_method" value="upi" checked>
                        <span>📱 <b>UPI / QR</b> (Google Pay, PhonePe, Paytm)</span>
                    </label>
                    <label style="display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer; background:#F8FAFC;">
                        <input type="radio" name="pay_method" value="card">
                        <span>💳 <b>Credit / Debit Card</b> (Visa, Mastercard, RuPay)</span>
                    </label>
                    <label style="display:flex; align-items:center; gap:10px; padding:10px 12px; border:1px solid #CBD5E1; border-radius:8px; cursor:pointer; background:#F8FAFC;">
                        <input type="radio" name="pay_method" value="netbanking">
                        <span>🏦 <b>Net Banking</b> (All Indian Banks)</span>
                    </label>
                </div>
            </div>

            <button onclick="completeSimulatedPayment('${orderId}', ${amount}, '${encodeURIComponent(prodName)}')" style="width:100%; background:#2563EB; color:white; border:none; padding:12px; border-radius:8px; font-size:15px; font-weight:bold; cursor:pointer; box-shadow:0 4px 6px -1px rgba(37,99,235,0.3);">
                Complete Payment Rs. ${amount.toLocaleString()}
            </button>
            <div style="font-size:11px; color:#94A3B8; text-align:center; margin-top:8px;">🔒 256-Bit Encrypted Razorpay Test Sandbox</div>
        </div>
    `;
    document.getElementById('checkout-modal').classList.remove('hidden');
}

function closeCheckoutModal() {
    document.getElementById('checkout-modal').classList.add('hidden');
}

async function completeSimulatedPayment(orderId, amount, encodedName) {
    const prodName = decodeURIComponent(encodedName);
    const content = document.getElementById('checkout-body-content');
    
    // Show spinner / capturing
    content.innerHTML = `
        <div style="text-align:center; padding:30px 10px;">
            <div style="font-size:36px; margin-bottom:10px;">🔄</div>
            <h3 style="color:#0F172A; margin:0 0 6px 0;">Processing Payment...</h3>
            <p style="color:#64748B; font-size:13px;">Capturing payment on Razorpay network</p>
        </div>
    `;

    // Trigger webhook verification in backend
    try {
        await fetch('/api/webhook-test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ order_id: orderId, tampered: false })
        });
    } catch(e) {}

    setTimeout(() => {
        content.innerHTML = `
            <div style="text-align:center; padding:20px 10px;">
                <div style="font-size:48px; margin-bottom:10px;">🎉</div>
                <h3 style="color:#059669; margin:0 0 8px 0;">Payment Captured Successfully!</h3>
                <p style="color:#0F172A; font-size:14px; margin:0 0 4px 0;">Paid <b>Rs. ${amount.toLocaleString()}</b> for <b>${prodName}</b></p>
                <p style="font-size:12px; color:#64748B;">Razorpay Payment ID: <code style="color:#2563EB;">pay_${orderId.replace('order_','')}</code></p>
                <div style="margin-top:16px;">
                    <button onclick="closeCheckoutModal()" style="background:#059669; color:white; border:none; padding:10px 20px; border-radius:6px; font-weight:bold; cursor:pointer;">
                        Done (View Receipt in Chat)
                    </button>
                </div>
            </div>
        `;

        // Announce voice confirmation
        speakOutLoud(`Payment of ${amount} rupees for ${prodName} has been captured successfully on Razorpay.`);

        // Append success message in stream
        const stream = document.getElementById('conversation-stream');
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble assistant';
        bubble.innerHTML = `
            <div><span style="color:#34D399; font-weight:bold;">🎉 PAYMENT CONFIRMED</span></div>
            <p style="margin-top:6px;">Payment of <b>Rs. ${amount.toLocaleString()}</b> captured successfully for <b>${prodName}</b> via Razorpay!</p>
            <div style="font-size:12px; color:#94A3B8;">Event logged in Merchant Audit Ledger.</div>
        `;
        stream.appendChild(bubble);
        stream.scrollTop = stream.scrollHeight;
    }, 1200);
}

// HITL Approval Modal
function openHitlModal() {
    if (!pendingHitlProduct) return;
    const p = pendingHitlProduct.product;
    const content = document.getElementById('modal-body-content');
    content.innerHTML = `
        <p>Do you authorize your AI Agent to purchase:</p>
        <h4 style="margin:8px 0; color:#38BDF8;">${p.name}</h4>
        <p>Price: <b>Rs. ${p.price_rupees.toLocaleString()}</b> from <b>${p.merchant_name}</b></p>
        <p style="font-size:12px; color:#94A3B8; margin-top:8px;">This will generate an official Razorpay order and payment link.</p>
    `;
    document.getElementById('hitl-modal').classList.remove('hidden');
}

function closeModal() {
    document.getElementById('hitl-modal').classList.add('hidden');
}

function confirmHumanApproval() {
    closeModal();
    if (pendingHitlProduct) {
        sendChatQuery(pendingHitlProduct.query, null, true);
        pendingHitlProduct = null;
    }
}

// Load Audit Logs
async function loadAuditLogs() {
    const tbody = document.getElementById('audit-table-body');
    try {
        const response = await fetch('/api/audit-log');
        const logs = await response.json();

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">No logs recorded yet.</td></tr>';
            return;
        }

        tbody.innerHTML = logs.map(l => {
            let summary = '';
            if (l.details.intent) summary += `Intent: "${l.details.intent}" `;
            if (l.details.product) summary += `Product: ${l.details.product} `;
            if (l.details.reasons) summary += `Block Reasons: ${l.details.reasons.join(', ')} `;
            if (l.details.order_id) summary += `Order: ${l.details.order_id} `;

            let eventColor = '#38BDF8';
            if (l.event.includes('declined') || l.event.includes('rejected')) eventColor = '#FCA5A5';
            if (l.event.includes('created') || l.event.includes('verified')) eventColor = '#34D399';

            return `
                <tr>
                    <td>${l.id}</td>
                    <td style="white-space:nowrap; color:#94A3B8;">${l.timestamp}</td>
                    <td style="color:${eventColor}; font-weight:600;">${l.event}</td>
                    <td style="font-size:12px; color:#CBD5E1;">${summary || JSON.stringify(l.details)}</td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Error fetching logs:', err);
    }
}

// Load Settings
async function loadSettings() {
    try {
        const res = await fetch('/api/settings');
        const config = await res.json();
        document.getElementById('setting-max-order').value = config.max_order_value;
        document.getElementById('setting-max-discount').value = config.max_discount_percent;
        document.getElementById('setting-daily-budget').value = config.max_daily_budget;
    } catch (err) {
        console.error('Error loading settings:', err);
    }
}

// Save Settings
async function saveSettings(e) {
    e.preventDefault();
    const max_order = document.getElementById('setting-max-order').value;
    const max_discount = document.getElementById('setting-max-discount').value;
    const daily_budget = document.getElementById('setting-daily-budget').value;

    try {
        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                max_order_value: max_order,
                max_discount_percent: max_discount,
                max_daily_budget: daily_budget
            })
        });
        alert('Policy settings saved successfully!');
        loadAuditLogs();
    } catch (err) {
        console.error('Error saving settings:', err);
    }
}

// Webhook Security Test
async function testWebhook(tampered) {
    const resBox = document.getElementById('webhook-result');
    resBox.style.display = 'block';
    resBox.textContent = 'Testing HMAC signature verification...';

    try {
        const response = await fetch('/api/webhook-test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: 'order_MOCK_test123', tampered })
        });
        const data = await response.json();

        if (tampered) {
            resBox.className = 'test-result-box badge-unverified';
            resBox.textContent = `❌ SECURITY BLOCK: ${data.message}`;
        } else {
            resBox.className = 'test-result-box badge-verified';
            resBox.textContent = `✅ SIGNATURE VERIFIED: ${data.message}`;
        }
        loadAuditLogs();
    } catch (err) {
        console.error('Webhook test error:', err);
    }
}
