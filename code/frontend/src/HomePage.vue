<template>
  <div class="container">
    <header>
      <div class="header-top">
        <h1>MedMirror: Towards Reliable Diagnosis in Traditional Chinese Medicine via Reflexive Interaction and Multi-Agent Collaboration</h1>
      </div>
      <p class="note">Instructions: Upload a tongue image to start diagnosis. The system will automatically run multiple agents for tongue diagnosis, information gathering, syndrome analysis, treatment planning, and report generation. The entire process will be displayed in real-time in the message area below.</p>
      
      <!-- Privacy Notice and Consent Mechanism -->
      <div class="privacy-section">
        <div class="privacy-notice">
          <h4>🔒 Privacy Protection Notice</h4>
          <div class="privacy-content">
            <p>• This system uses only non-identifiable data and does not collect or store any personal identification information</p>
            <p>• All interaction data will be automatically destroyed within 24 hours and will not be permanently stored</p>
            <p>• Tongue diagnosis images are used solely for medical analysis and will not be used for other purposes</p>
            <p>• The system uses end-to-end encrypted transmission to ensure data security</p>
          </div>
        </div>
        <div class="consent-section">
          <label class="consent-checkbox">
            <input type="checkbox" id="privacyConsent" onchange="updateConsentStatus()">
            <span class="checkmark"></span>
            <span class="consent-text">I have read and agree to the above privacy protection terms and consent to use this system</span>
          </label>
        </div>
      </div>
      
      <p id="status">Ready</p>
    </header>

    <section>
      <h3>Tongue Image Upload & Diagnosis</h3>
      <div class="row">
        <div class="file-input-wrapper">
          <input id="tongue" type="file" accept="image/*" onchange="updateFileDisplay()" />
          <label for="tongue" class="file-input-label" id="fileInputLabel">Choose File</label>
        </div>
        <button onclick="uploadTongue()" id="uploadBtn" disabled>Upload & Start Diagnosis</button>
        <button onclick="clearSession()" id="clearBtn" style="display: none;">Clear Session</button>
      </div>
      <div class="col">
        <div id="fileInfo" class="file-info" style="display: none;"></div>
        <div class="diagnosis-section">
          <div class="diagnosis-header">
            <h4>Tongue Diagnosis Result</h4>
            <div class="diagnosis-status" id="diagnosisStatus" style="display: none;">
              <span class="status-indicator"></span>
              <span class="status-text">Analyzing...</span>
            </div>
          </div>
          <div class="diagnosis-content" id="diagnosis" style="display: none;">
            <div class="diagnosis-placeholder">
              <div class="placeholder-icon">🔍</div>
              <p>Diagnosis results will appear here after analysis</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section>
      <h3>Patient Information Collection</h3>
      <div class="col">
        <label>Patient Information Input</label>
        <div id="latestInfoMsg" class="message info" style="display:none;">
          <div class="message-header">
            <span class="agent-name">ClinicalInterviewAgent</span>
          </div>
          <div class="message-content" id="latestInfoContent"></div>
        </div>
        <textarea id="userMessage" placeholder="Please provide patient information as requested by the ClinicalInterviewAgent..."></textarea>
        <div class="row">
          <button onclick="sendMessage()" id="sendBtn" disabled>Send Message</button>
          <span id="messageStatus" style="display: none; color: var(--muted); font-size: 14px;">Sending...</span>
        </div>
      </div>
      <div class="col" style="display:none;">
        <strong>ClinicalInterviewAgent Dialogue (hidden)</strong>
        <div id="dialogueContainer" style="display: none;"></div>
      </div>
    </section>

    <section>
      <h3>Real-time Diagnosis Process</h3>
      <div class="col">
        <strong>Agent Status and Messages</strong>
        <div id="messagesContainer">
          <div class="message info">
            <div class="message-header">
              <span class="agent-name">System</span>
              <span class="timestamp">Waiting to start...</span>
            </div>
            <div class="message-content">Please upload a tongue image to start the diagnosis process.</div>
          </div>
        </div>
      </div>
    </section>

    <section>
      <h3>Diagnosis Report</h3>
      <div class="row">
        <a id="reportLink" href="#" target="_blank" style="display: none;" class="primary">Download Diagnosis Report</a>
        <span id="reportStatus" style="display: none; color: var(--muted);">Generating report...</span>
      </div>
    </section>

    <section>
      <h3>System Information</h3>
      <div class="col">
        <div id="sessionInfo" style="color: var(--muted); font-size: 14px;">
          Session ID: <span id="sessionIdDisplay">Not started</span><br>
          Current Status: <span id="currentStatus">Idle</span><br>
          Runtime: <span id="runTime">0 seconds</span>
        </div>
      </div>
    </section>

    <section>
      <h3>Survey</h3>
      <div class="row">
        <button @click="goToSurvey" class="btn btn-ghost">Take Survey</button>
      </div>
    </section>
  </div>
  <pre id="log" style="display:none;"></pre>
</template>

<script>
export default {
  name: 'HomePage',
  methods: {
    goToSurvey() {
      this.$router.push('/survey');
    }
  },
  mounted() {
    const API = (() => {
      try {
        const u = new URL(window.location.href);
        const protocol = u.protocol.startsWith('http') ? u.protocol : 'http:';
        const hostname = u.hostname || 'localhost';
        return `${protocol}//${hostname}:8000`;
      } catch (e) {
        return 'http://localhost:8000';
      }
    })();

    let currentSessionId = null;
    let pollingInterval = null;
    let isPolling = false;
    let selectedFileMeta = null;
    let displayedMessageIds = new Set(); // 跟踪已显示的消息ID
    let lastMessageCount = 0; // 跟踪上次消息数量
    let userConsented = false; // 用户是否同意隐私条款

    function setStatus(text, ok) {
      const s = document.getElementById('status');
      if (!s) return;
      s.textContent = text;
      s.className = ok === undefined ? '' : (ok ? 'ok' : 'err');
    }

    function updateConsentStatus() {
      const consentCheckbox = document.getElementById('privacyConsent');
      const uploadBtn = document.getElementById('uploadBtn');
      const sendBtn = document.getElementById('sendBtn');
      const fileInput = document.getElementById('tongue');
      const userMessage = document.getElementById('userMessage');
      
      userConsented = consentCheckbox.checked;
      
      if (userConsented) {
        // Enable all interaction functions
        uploadBtn.disabled = false;
        sendBtn.disabled = false;
        fileInput.disabled = false;
        userMessage.disabled = false;
        setStatus('Privacy terms agreed, you can now start using the system', true);
      } else {
        // Disable all interaction functions
        uploadBtn.disabled = true;
        sendBtn.disabled = true;
        fileInput.disabled = true;
        userMessage.disabled = true;
        setStatus('Please read and agree to the privacy protection terms first', false);
      }
    }

    async function getJSON(url) {
      try {
        const res = await fetch(API + url);
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
        return json;
      } catch (err) {
        return { ok: false, error: err?.message || 'Network error' };
      }
    }

    async function postJSON(url, data) {
      try {
        const res = await fetch(API + url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data)
        });
        const json = await res.json();
        if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
        return json;
      } catch (err) {
        return { ok: false, error: err?.message || 'Network error' };
      }
    }

    async function postFile(url, file) {
      const fd = new FormData();
      fd.append('image', file);
      try {
        const res = await fetch(API + url, { method: 'POST', body: fd });
        const text = await res.text();
        const json = text ? JSON.parse(text) : {};
        if (!res.ok || json.ok === false) throw new Error(json.error || `HTTP ${res.status}`);
        return json;
      } catch (err) {
        return { ok: false, error: err?.message || 'Network error' };
      }
    }

    async function checkServerConnection() {
      try {
        const data = await getJSON('/api/health');
        if (data.status === 'healthy') setStatus('Server connected, ready to use', true);
        else setStatus('Server status abnormal', false);
      } catch (err) {
        setStatus('Cannot connect to server, please check if server is running', false);
      }
    }

    function updateDialogueDisplay(data) {
      // 仅显示最新一条 ClinicalInterviewAgent 或 System(包含ClinicalInterviewAgent) 的消息
      const infoMessages = (data.messages || []).filter(msg =>
        msg.agent === 'ClinicalInterviewAgent' || (msg.agent === 'System' && msg.message.includes('ClinicalInterviewAgent'))
      );
      const latest = infoMessages.length ? infoMessages[infoMessages.length - 1] : null;
      const latestBox = document.getElementById('latestInfoMsg');
      const latestContent = document.getElementById('latestInfoContent');
      if (!latestBox || !latestContent) return;
      if (!latest) {
        latestBox.style.display = 'none';
        return;
      }
      latestBox.className = `message ${latest.type}`;
      latestContent.textContent = latest.message;
      latestBox.style.display = 'block';
    }

    function updateStatusDisplay(data) {
      setStatus(`Current Step: ${data.current_step}`, true);
      const sid = document.getElementById('sessionIdDisplay');
      const cst = document.getElementById('currentStatus');
      if (sid) sid.textContent = data.session_id || 'Unknown';
      if (cst) cst.textContent = data.status || 'Unknown';
      if (data.created_at) {
        const startTime = new Date(data.created_at);
        const now = new Date();
        const runTime = Math.floor((now - startTime) / 1000);
        const rt = document.getElementById('runTime');
        if (rt) rt.textContent = `${runTime} seconds`;
      }
      
      // 增量更新消息列表
      updateMessagesIncremental(data.messages || []);
      
      // 若后端包含舌诊结果，则展示
      if (data && data.data && data.data.tongue_coating_diagnosis) {
        const diagnosisEl = document.getElementById('diagnosis');
        const diagnosisStatus = document.getElementById('diagnosisStatus');
        if (diagnosisEl) {
          // 隐藏占位符，显示实际结果
          const placeholder = diagnosisEl.querySelector('.diagnosis-placeholder');
          if (placeholder) placeholder.style.display = 'none';
          
          // 创建结果内容
          const resultContent = document.createElement('div');
          resultContent.className = 'diagnosis-result';
          resultContent.innerHTML = `
            <div class="result-header">
              <span class="result-icon">📋</span>
              <span class="result-title">Diagnosis Complete</span>
            </div>
            <div class="result-content">${data.data.tongue_coating_diagnosis}</div>
          `;
          
          // 清除旧内容并添加新内容
          diagnosisEl.innerHTML = '';
          diagnosisEl.appendChild(resultContent);
          diagnosisEl.style.display = 'block';
          
          // 更新状态
          if (diagnosisStatus) {
            diagnosisStatus.querySelector('.status-text').textContent = 'Complete';
            diagnosisStatus.querySelector('.status-indicator').className = 'status-indicator completed';
          }
        }
      }
      updateDialogueDisplay(data);
    }

    function updateMessagesIncremental(messages) {
      const messagesContainer = document.getElementById('messagesContainer');
      if (!messagesContainer) return;
      
      messagesContainer.style.display = 'block';
      
      // 如果消息数量没有变化，不进行更新
      if (messages.length === lastMessageCount) return;
      
      // 记录当前滚动位置
      const wasAtBottom = messagesContainer.scrollTop + messagesContainer.clientHeight >= messagesContainer.scrollHeight - 5;
      
      // 只添加新消息
      messages.forEach((msg, index) => {
        // 使用索引+时间戳作为唯一标识符
        const messageId = `${index}_${msg.timestamp}_${msg.agent}`;
        
        if (!displayedMessageIds.has(messageId)) {
          const messageDiv = document.createElement('div');
          messageDiv.className = `message ${msg.type}`;
          messageDiv.innerHTML = `
            <div class="message-header"><span class="agent-name">${msg.agent}</span></div>
            <div class="message-content">${msg.message}</div>
          `;
          messagesContainer.appendChild(messageDiv);
          displayedMessageIds.add(messageId);
        }
      });
      
      // 更新消息计数
      lastMessageCount = messages.length;
      
      // 如果用户之前在底部，则滚动到底部；否则保持当前位置
      if (wasAtBottom) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
      }
    }

    function showReportLink(reportPath) {
      if (!reportPath) return;
      const reportLink = document.getElementById('reportLink');
      if (reportLink) {
        const sessionId = currentSessionId || 'unknown';
        // 使用新的完整诊断包下载端点
        reportLink.href = API + '/api/download_package/' + encodeURIComponent(sessionId);
        reportLink.textContent = 'Download Complete Diagnosis Package';
        reportLink.style.display = 'inline-block';
      }
    }

    function startPolling(sessionId) {
      if (isPolling) return;
      isPolling = true;
      currentSessionId = sessionId;
      (async () => {
        try {
          let data = await getJSON(`/api/status/${sessionId}`);
          if (data.error) {
            const data2 = await getJSON(`/api/messages/${sessionId}`);
            if (!data2.error) data = Object.assign({ session_id: sessionId, status: 'unknown', current_step: '' }, data2);
            else { setStatus('Polling error: ' + data.error, false); return; }
          }
          updateStatusDisplay(data);
          if (data.status === 'completed' || data.status === 'error') {
            stopPolling();
            if (data.status === 'completed') { setStatus('Diagnosis process completed!', true); showReportLink(data.data && data.data.report_save_path); }
            else { setStatus('Diagnosis process error: ' + data.error_message, false); }
          }
        } catch (err) { setStatus('Polling failed: ' + err.message, false); }
      })();
      pollingInterval = setInterval(async () => {
        try {
          let data = await getJSON(`/api/status/${sessionId}`);
          if (data.error) {
            const data2 = await getJSON(`/api/messages/${sessionId}`);
            if (!data2.error) data = Object.assign({ session_id: sessionId, status: 'unknown', current_step: '' }, data2);
            else { setStatus('Polling error: ' + data.error, false); return; }
          }
          updateStatusDisplay(data);
          if (data.status === 'completed' || data.status === 'error') {
            stopPolling();
            if (data.status === 'completed') { setStatus('Diagnosis process completed!', true); showReportLink(data.data && data.data.report_save_path); }
            else { setStatus('Diagnosis process error: ' + data.error_message, false); }
          }
        } catch (err) { setStatus('Polling failed: ' + err.message, false); }
      }, 2000);
    }

    function stopPolling() {
      if (pollingInterval) { clearInterval(pollingInterval); pollingInterval = null; }
      isPolling = false;
    }

    async function uploadTongueInner() {
      if (!userConsented) {
        return setStatus('Please agree to the privacy protection terms first to use the system', false);
      }
      
      const fileInput = document.getElementById('tongue');
      const uploadBtn = document.getElementById('uploadBtn');
      const clearBtn = document.getElementById('clearBtn');
      if (!fileInput?.files || !fileInput.files[0]) return setStatus('Please select an image file first', false);
      uploadBtn.disabled = true;
      uploadBtn.innerHTML = '<span class="progress-indicator"></span>Uploading...';
      setStatus('Uploading tongue image...', true);
      try {
        const uploadData = await postFile('/api/upload_image', fileInput.files[0]);
        if (uploadData.error) throw new Error(uploadData.error);
        setStatus('Image uploaded successfully, starting diagnosis process...', true);
        uploadBtn.innerHTML = '<span class="progress-indicator"></span>Diagnosing...';
        const diagnosisData = await postJSON('/api/start_diagnosis', { image_path: uploadData.image_path });
        if (diagnosisData.error) throw new Error(diagnosisData.error);
        currentSessionId = diagnosisData.session_id;
        setStatus('Diagnosis process started, processing...', true);
        startPolling(currentSessionId);
        uploadBtn.style.display = 'none';
        clearBtn.style.display = 'inline-block';
        document.getElementById('reportStatus').style.display = 'inline-block';
        document.getElementById('dialogueContainer').style.display = 'block';
        if (uploadData.diagnosis) {
          const diagnosisEl = document.getElementById('diagnosis');
          const diagnosisStatus = document.getElementById('diagnosisStatus');
          if (diagnosisEl) {
            // 显示分析状态
            if (diagnosisStatus) {
              diagnosisStatus.style.display = 'flex';
            }
            
            // 创建结果内容
            const resultContent = document.createElement('div');
            resultContent.className = 'diagnosis-result';
            resultContent.innerHTML = `
              <div class="result-header">
                <span class="result-icon">📋</span>
                <span class="result-title">Diagnosis Complete</span>
              </div>
              <div class="result-content">${uploadData.diagnosis}</div>
            `;
            
            // 清除旧内容并添加新内容
            diagnosisEl.innerHTML = '';
            diagnosisEl.appendChild(resultContent);
            diagnosisEl.style.display = 'block';
            
            // 更新状态
            if (diagnosisStatus) {
              diagnosisStatus.querySelector('.status-text').textContent = 'Complete';
              diagnosisStatus.querySelector('.status-indicator').className = 'status-indicator completed';
            }
          }
        }
      } catch (err) {
        setStatus('Upload or diagnosis failed: ' + err.message, false);
        const uploadBtn2 = document.getElementById('uploadBtn');
        uploadBtn2.disabled = false;
        uploadBtn2.innerHTML = 'Upload & Start Diagnosis';
      }
    }

    async function sendMessageInner() {
      if (!userConsented) {
        return setStatus('Please agree to the privacy protection terms first to use the system', false);
      }
      
      const messageInput = document.getElementById('userMessage');
      const sendBtn = document.getElementById('sendBtn');
      const messageStatus = document.getElementById('messageStatus');
      const message = (messageInput.value || '').trim();
      if (!message) return setStatus('Please enter a message', false);
      if (!currentSessionId) return setStatus('No active session', false);
      sendBtn.disabled = true;
      messageStatus.style.display = 'inline';
      messageStatus.textContent = 'Sending...';
      try {
        const response = await postJSON(`/api/send_message/${currentSessionId}`, { message });
        if (response.error) throw new Error(response.error);
        messageInput.value = '';
        messageStatus.textContent = 'Message sent successfully';
        const statusData = await getJSON(`/api/status/${currentSessionId}`);
        updateStatusDisplay(statusData);
      } catch (err) {
        setStatus('Failed to send message: ' + err.message, false);
        messageStatus.textContent = 'Failed to send message';
      } finally {
        sendBtn.disabled = false;
        setTimeout(() => { messageStatus.style.display = 'none'; }, 2000);
      }
    }

    function clearSessionInner() {
      if (currentSessionId) {
        fetch(API + `/api/clear_session/${currentSessionId}`, { method: 'DELETE' });
        currentSessionId = null;
      }
      stopPolling();
      
      // 重置消息跟踪状态
      displayedMessageIds.clear();
      lastMessageCount = 0;
      
      document.getElementById('uploadBtn').style.display = 'inline-block';
      document.getElementById('uploadBtn').disabled = false;
      document.getElementById('uploadBtn').innerHTML = 'Upload & Start Diagnosis';
      document.getElementById('clearBtn').style.display = 'none';
      document.getElementById('reportStatus').style.display = 'none';
      document.getElementById('reportLink').style.display = 'none';
      document.getElementById('messagesContainer').style.display = 'none';
      document.getElementById('dialogueContainer').style.display = 'none';
      // 重置诊断结果区域
      const diagnosisEl = document.getElementById('diagnosis');
      const diagnosisStatus = document.getElementById('diagnosisStatus');
      if (diagnosisEl) {
        diagnosisEl.style.display = 'none';
        diagnosisEl.innerHTML = `
          <div class="diagnosis-placeholder">
            <div class="placeholder-icon">🔍</div>
            <p>Diagnosis results will appear here after analysis</p>
          </div>
        `;
      }
      if (diagnosisStatus) {
        diagnosisStatus.style.display = 'none';
        diagnosisStatus.querySelector('.status-text').textContent = 'Analyzing...';
        diagnosisStatus.querySelector('.status-indicator').className = 'status-indicator';
      }
      document.getElementById('latestInfoMsg').style.display = 'none';
      document.getElementById('sessionIdDisplay').textContent = 'Not started';
      document.getElementById('currentStatus').textContent = 'Idle';
      document.getElementById('runTime').textContent = '0 seconds';
      setStatus('Session cleared, ready to start again', true);
    }

    function updateFileDisplayInner() {
      const fileInput = document.getElementById('tongue');
      const fileInfo = document.getElementById('fileInfo');
      const fileInputLabel = document.getElementById('fileInputLabel');
      
      if (fileInput.files && fileInput.files[0]) {
        const file = fileInput.files[0];
        const fileSize = (file.size / 1024 / 1024).toFixed(2);
        selectedFileMeta = { name: file.name, sizeMB: fileSize };
        fileInfo.innerHTML = `
          <div class="file-info-content">
            <span class="file-icon">📁</span>
            <div class="file-details">
              <div class="file-name">${selectedFileMeta.name}</div>
              <div class="file-size">${selectedFileMeta.sizeMB} MB</div>
            </div>
          </div>
        `;
        fileInfo.style.display = 'block';
        
        // 更新自定义标签的文字和样式
        fileInputLabel.textContent = 'File Selected';
        fileInputLabel.classList.add('has-file');
      } else {
        // 重置自定义标签的文字和样式
        fileInputLabel.textContent = 'Choose File';
        fileInputLabel.classList.remove('has-file');
        
        if (selectedFileMeta) {
          fileInfo.innerHTML = `
            <div class="file-info-content">
              <span class="file-icon">📁</span>
              <div class="file-details">
                <div class="file-name">${selectedFileMeta.name}</div>
                <div class="file-size">${selectedFileMeta.sizeMB} MB</div>
              </div>
            </div>
          `;
          fileInfo.style.display = 'block';
        }
      }
    }

    // 挂载到 window，供模板内 inline 事件调用
    window.uploadTongue = uploadTongueInner;
    window.clearSession = clearSessionInner;
    window.sendMessage = sendMessageInner;
    window.updateFileDisplay = updateFileDisplayInner;
    window.updateConsentStatus = updateConsentStatus;

    checkServerConnection();
  }
}
</script>

<style>
  /* HomePage 特定样式 */
  .container { max-width: 1080px; margin: 0 auto; padding: 32px 20px 40px; }
  header { margin-bottom: 24px; }
  .header-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  h1 { margin: 0; font-weight: 700; line-height: 1.25; letter-spacing: -0.02em; font-size: 28px; background: linear-gradient(90deg, #3b82f6, #10b981); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .note { color: var(--muted); margin: 8px 0 0 0; font-size: 14px; line-height: 1.5; }
  
  /* 隐私说明区域样式 */
  .privacy-section {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }
  
  .privacy-notice h4 {
    margin: 0 0 12px 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .privacy-content {
    margin-bottom: 16px;
  }
  
  .privacy-content p {
    margin: 6px 0;
    font-size: 14px;
    line-height: 1.5;
    color: var(--muted);
  }
  
  .consent-section {
    border-top: 1px solid #e2e8f0;
    padding-top: 16px;
  }
  
  .consent-checkbox {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    cursor: pointer;
    font-size: 14px;
    line-height: 1.5;
    color: var(--text);
  }
  
  .consent-checkbox input[type="checkbox"] {
    display: none;
  }
  
  .checkmark {
    width: 20px;
    height: 20px;
    border: 2px solid #d1d5db;
    border-radius: 4px;
    background: white;
    position: relative;
    flex-shrink: 0;
    transition: all 0.2s ease;
  }
  
  .consent-checkbox input[type="checkbox"]:checked + .checkmark {
    background: var(--accent);
    border-color: var(--accent);
  }
  
  .consent-checkbox input[type="checkbox"]:checked + .checkmark::after {
    content: '✓';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: white;
    font-size: 12px;
    font-weight: bold;
  }
  
  .consent-checkbox:hover .checkmark {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  }
  
  .consent-text {
    flex: 1;
    font-weight: 500;
  }
  section { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-top: 16px; box-shadow: var(--shadow); }
  h3 { margin: 0 0 16px 0; font-size: 18px; color: var(--text); font-weight: 600; }
  .row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  .col { display: flex; flex-direction: column; gap: 12px; }
  textarea { width: 100%; min-height: 120px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; background: #f8fafc; color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 12px; resize: vertical; font-size: 16px; }
  textarea:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
  /* 完全自定义文件选择器 */
  input[type="file"] {
    position: absolute;
    opacity: 0;
    width: 0;
    height: 0;
    overflow: hidden;
  }
  
  .file-input-wrapper {
    position: relative;
    display: inline-block;
  }
  
  .file-input-label {
    display: inline-block;
    background: var(--accent);
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.2s ease;
    border: none;
    font-size: 14px;
  }
  
  .file-input-label:hover {
    background: #2563eb;
  }
  
  .file-input-label.has-file {
    background: var(--accent-2);
  }
  
  .file-input-label.has-file:hover {
    background: #059669;
  }

  pre { white-space: pre-wrap; background: #f8fafc; color: var(--text); padding: 16px; border-radius: 8px; max-height: 300px; overflow: auto; border: 1px solid var(--border); font-size: 16px; line-height: 1.5; }
  button { padding: 12px 16px; border: 1px solid var(--border); border-radius: 8px; background: var(--card); color: var(--text); cursor: pointer; transition: all .2s ease; font-weight: 500; }
  button:hover { transform: translateY(-1px); border-color: var(--accent); box-shadow: var(--shadow); }
  button.primary { background: linear-gradient(90deg, var(--accent), var(--accent-2)); color: white; border-color: transparent; }
  button.primary:hover { box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
  button:disabled { opacity: 0.6; cursor: not-allowed; }
  #status { margin: 8px 0 0 0; font-size: 14px; font-weight: 500; }
  .ok { color: var(--accent-2); }
  .err { color: #ef4444; }
  label { font-weight: 500; color: var(--text); }
  strong { color: var(--text); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  #messagesContainer { max-height: 400px; overflow-y: auto; border: 1px solid var(--border); border-radius: 8px; padding: 12px; background: #f8fafc; margin-top: 12px; }
  .message { margin-bottom: 12px; padding: 8px 12px; border-radius: 6px; border-left: 3px solid var(--border); }
  .message.info { background: #f0f9ff; border-left-color: var(--accent); }
  .message.success { background: #f0fdf4; border-left-color: var(--accent-2); }
  .message.warning { background: #fffbeb; border-left-color: #f59e0b; }
  .message.error { background: #fef2f2; border-left-color: #ef4444; }
  .message-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
  .agent-name { font-weight: 600; color: var(--text); }
  .timestamp { font-size: 12px; color: var(--muted); }
  .message-content { font-size: 14px; line-height: 1.5; color: var(--text); white-space: pre-wrap; }
  .progress-indicator { display: inline-block; width: 12px; height: 12px; border: 2px solid var(--accent); border-radius: 50%; border-top-color: transparent; animation: spin 1s linear infinite; margin-right: 8px; }
  @keyframes spin { to { transform: rotate(360deg); } }
  
  /* 文件信息样式 */
  .file-info {
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border: 1px solid #bae6fd;
    border-radius: 8px;
    padding: 12px;
    margin: 8px 0;
  }
  
  .file-info-content {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  
  .file-icon {
    font-size: 20px;
    color: var(--accent);
  }
  
  .file-details {
    flex: 1;
  }
  
  .file-name {
    font-weight: 600;
    color: var(--text);
    font-size: 14px;
    margin-bottom: 2px;
  }
  
  .file-size {
    font-size: 12px;
    color: var(--muted);
  }
  
  /* 诊断结果区域样式 */
  .diagnosis-section {
    margin-top: 16px;
  }
  
  .diagnosis-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }
  
  .diagnosis-header h4 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
  }
  
  .diagnosis-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: #fef3c7;
    border: 1px solid #f59e0b;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 500;
  }
  
  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #f59e0b;
    animation: pulse 2s infinite;
  }
  
  .status-indicator.completed {
    background: var(--accent-2);
    animation: none;
  }
  
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  
  .diagnosis-content {
    background: #f8fafc;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
  }
  
  .diagnosis-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 40px 20px;
    text-align: center;
    color: var(--muted);
  }
  
  .placeholder-icon {
    font-size: 32px;
    margin-bottom: 12px;
    opacity: 0.6;
  }
  
  .diagnosis-placeholder p {
    margin: 0;
    font-size: 14px;
  }
  
  .diagnosis-result {
    padding: 0;
  }
  
  .result-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 16px 20px;
    background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
    border-bottom: 1px solid #bae6fd;
  }
  
  .result-icon {
    font-size: 18px;
  }
  
  .result-title {
    font-weight: 600;
    color: var(--text);
    font-size: 14px;
  }
  
  .result-content {
    padding: 20px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text);
    white-space: pre-wrap;
    background: white;
    max-height: 300px;
    overflow-y: auto;
  }
  
  /* 响应式设计 */
  @media (max-width: 768px) {
    .diagnosis-header {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
    
    .diagnosis-status {
      align-self: flex-end;
    }
    
    .file-info-content {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }
    
    .result-content {
      font-size: 13px;
      padding: 16px;
    }
    
    .privacy-section {
      padding: 16px;
      margin: 12px 0;
    }
    
    .privacy-notice h4 {
      font-size: 15px;
    }
    
    .privacy-content p {
      font-size: 13px;
    }
    
    .consent-checkbox {
      font-size: 13px;
    }
    
    .consent-text {
      line-height: 1.4;
    }
  }
</style>
