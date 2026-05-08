<template>
  <main class="container">
    <header class="header">
      <h1 class="title">MedMirror: Towards Reliable Diagnosis in Traditional Chinese Medicine via Reflexive Interaction and Multi-Agent Collaboration</h1>
      <p class="note">Please rate each dimension from 1 (severely deficient) to 7 (excellent). Provide your demographic information and overall impressions. Your responses are anonymous and will be used for research purposes only.</p>
    </header>

    <form id="evaluation-form" class="card" novalidate @submit.prevent="submitForm">
      <section class="section">
        <h3 class="section-title">Participant Information</h3>
        <div class="grid-2">
          <div class="field">
            <label for="gender">Gender</label>
            <select id="gender" name="gender" v-model="formData.gender" required>
              <option value="" disabled>Select</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="nonbinary">Non-binary</option>
              <option value="prefer_not">Prefer not to say</option>
              <option value="other">Other</option>
            </select>
            <div class="hint">Required</div>
          </div>
          <div class="field">
            <label for="age">Age</label>
            <input id="age" name="age" type="number" min="10" max="120" placeholder="e.g., 28" v-model="formData.age" required />
            <div class="hint">Required (10 - 120)</div>
          </div>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">Core Dimensions (1 - 7)</h3>

        <div class="likert-group">
          <div class="likert-item" v-for="(item, index) in likertItems" :key="index">
            <div class="likert-label">
              <span>{{ item.title }}</span>
              <small>{{ item.description }}</small>
            </div>
            <div class="likert-scale">
              <div v-for="i in 7" :key="i" class="likert-option">
                <input 
                  :id="`${item.name}_${i}`" 
                  :name="item.name" 
                  type="radio" 
                  :value="i" 
                  v-model="formData[item.name]"
                  required
                />
                <label :for="`${item.name}_${i}`">{{ i }}</label>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="section">
        <h3 class="section-title">Overall Impressions</h3>
        <div class="field">
          <label for="impressions">Your thoughts, suggestions, or concerns</label>
          <textarea id="impressions" name="impressions" rows="5" placeholder="Write your overall impressions here (optional)" v-model="formData.impressions"></textarea>
        </div>
      </section>

      <div class="actions">
        <button type="submit" class="btn" :disabled="isSubmitting">
          {{ isSubmitting ? 'Submitting...' : 'Submit' }}
        </button>
        <button type="reset" class="btn btn-ghost" @click="resetForm">Reset</button>
        <button type="button" class="btn btn-ghost" @click="goToMain">Back to System</button>
      </div>
    </form>

    <div v-if="showThankYou" class="thank-you">
      <h2>Thank you!</h2>
      <p>Your evaluation has been recorded. You may now close this page or return to the system.</p>
      <div class="actions">
        <button class="btn" @click="goToMain">Back to System</button>
        <button class="btn btn-ghost" @click="resetForm">Submit Another</button>
      </div>
      <pre v-if="showResult" class="result">{{ JSON.stringify(formData, null, 2) }}</pre>
    </div>
  </main>
</template>

<script>
export default {
  name: 'SurveyView',
  data() {
    return {
      formData: {
        gender: '',
        age: null,
        overall_experience: null,
        ease_of_use: null,
        response_speed: null,
        info_understandability: null,
        info_comprehensiveness: null,
        info_relevance: null,
        info_quality_credibility: null,
        privacy_protection: null,
        impressions: ''
      },
      likertItems: [
        {
          name: 'overall_experience',
          title: '1) Overall user experience',
          description: 'General satisfaction with the system'
        },
        {
          name: 'ease_of_use',
          title: '2) Ease of use',
          description: 'How easy the system is to operate'
        },
        {
          name: 'response_speed',
          title: '3) Response speed',
          description: 'System responsiveness and latency'
        },
        {
          name: 'info_understandability',
          title: '4) Information understandability',
          description: 'Clarity and readability of presented information'
        },
        {
          name: 'info_comprehensiveness',
          title: '5) Information comprehensiveness',
          description: 'Coverage and completeness of information'
        },
        {
          name: 'info_relevance',
          title: '6) Information relevance',
          description: 'Relevance of information to the task'
        },
        {
          name: 'info_quality_credibility',
          title: '7) Information quality & credibility',
          description: 'Perceived accuracy and trustworthiness'
        },
        {
          name: 'privacy_protection',
          title: '8) Privacy protection',
          description: 'Protection of personal data'
        }
      ],
      isSubmitting: false,
      showThankYou: false,
      showResult: false
    }
  },
  methods: {
    async submitForm() {
      if (!this.validateForm()) {
        return;
      }

      this.isSubmitting = true;
      
      try {
        // 获取API基础URL
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

        const response = await fetch(API + '/api/submit_survey', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            ...this.formData,
            timestamp: new Date().toISOString(),
            user_agent: navigator.userAgent
          })
        });

        if (response.ok) {
          const result = await response.json();
          console.log('Survey submitted successfully:', result);
          this.showThankYou = true;
          this.showResult = true;
        } else {
          // 尝试解析错误响应
          let errorMessage = 'Unknown error';
          try {
            const errorData = await response.json();
            errorMessage = errorData.error || errorMessage;
          } catch (parseError) {
            // 如果不是JSON，获取文本内容
            const textResponse = await response.text();
            console.error('Non-JSON error response:', textResponse);
            errorMessage = `Server error (${response.status}): ${textResponse.substring(0, 100)}`;
          }
          alert('Failed to submit survey: ' + errorMessage);
        }
      } catch (error) {
        console.error('Network error:', error);
        alert('Network error: ' + error.message);
      } finally {
        this.isSubmitting = false;
      }
    },
    
    validateForm() {
      const required = ['gender', 'age', 'overall_experience', 'ease_of_use', 'response_speed', 
                       'info_understandability', 'info_comprehensiveness', 'info_relevance', 
                       'info_quality_credibility', 'privacy_protection'];
      
      for (const field of required) {
        if (!this.formData[field]) {
          alert(`Please fill in all required fields. Missing: ${field}`);
          return false;
        }
      }
      
      if (this.formData.age < 10 || this.formData.age > 120) {
        alert('Age must be between 10 and 120');
        return false;
      }
      
      return true;
    },
    
    resetForm() {
      this.formData = {
        gender: '',
        age: null,
        overall_experience: null,
        ease_of_use: null,
        response_speed: null,
        info_understandability: null,
        info_comprehensiveness: null,
        info_relevance: null,
        info_quality_credibility: null,
        privacy_protection: null,
        impressions: ''
      };
      this.showThankYou = false;
      this.showResult = false;
    },
    
    goToMain() {
      this.$router.push('/');
    }
  }
}
</script>

<style>
/* SurveyView 特定样式 */

.container {
  max-width: 1080px;
  margin: 0 auto;
  padding: 32px 20px 40px;
}

.header {
  margin-bottom: 24px;
}

.title {
  margin: 0;
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.02em;
  font-size: 28px;
  background: linear-gradient(90deg, #3b82f6, #10b981);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.note {
  color: var(--muted);
  margin: 8px 0 0 0;
  font-size: 14px;
  line-height: 1.5;
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
}

.section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  margin-top: 16px;
  box-shadow: var(--shadow);
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  color: var(--text);
  font-weight: 600;
}

.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

label {
  font-size: 14px;
}

input[type="number"], select, textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: #fff;
  outline: none;
  transition: border-color .15s ease, box-shadow .15s ease;
}

input[type="number"]:focus, select:focus, textarea:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.25);
}

.hint {
  font-size: 12px;
  color: var(--muted);
}

.likert-group {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.likert-item {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 20px;
}

.likert-label span { font-weight: 500; }
.likert-label small { color: var(--muted); display: block; margin-top: 2px; }

.likert-scale {
  display: grid;
  grid-template-columns: repeat(7, 36px);
  gap: 6px;
}

.likert-option {
  position: relative;
}

.likert-scale input[type="radio"] {
  display: none;
}

.likert-scale label {
  display: grid;
  place-items: center;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--border);
  color: var(--muted);
  cursor: pointer;
  transition: all .15s ease;
  background: #fff;
  margin: 0;
}

.likert-scale input[type="radio"]:checked + label {
  background: var(--accent);
  border-color: var(--accent);
  color: #fff;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.25);
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid var(--accent);
  background: var(--accent);
  color: #fff;
  cursor: pointer;
  transition: filter .15s ease;
  font-size: 14px;
}

.btn:hover:not(:disabled) { 
  filter: brightness(0.95); 
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-ghost {
  background: transparent;
  color: var(--accent);
}

.thank-you {
  text-align: center;
  margin-top: 20px;
}

.result {
  text-align: left;
  background: #0b1021;
  color: #d1d5db;
  padding: 14px;
  border-radius: 10px;
  overflow: auto;
  margin-top: 16px;
  font-size: 12px;
}

@media (max-width: 640px) {
  .grid-2 { grid-template-columns: 1fr; }
  .likert-item { grid-template-columns: 1fr; }
  .likert-scale { grid-template-columns: repeat(7, 1fr); }
  .actions { justify-content: center; }
}
</style>
