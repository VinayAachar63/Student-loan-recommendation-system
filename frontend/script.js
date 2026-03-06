function qs(id){ return document.getElementById(id); }

// ... (toggleSection, onStudyTypeChange, onUnivLevelChange, computePercentage, displayCGPA, computeTotalAmount, submitForm, showRecommendations functions are unchanged) ...
function toggleSection(selectId, sections){
  const value = qs(selectId).value;
  for (const section in sections) {
    if (section === value) {
      qs(sections[section]).classList.remove('hidden');
    } else {
      qs(sections[section]).classList.add('hidden');
    }
  }
}
function onStudyTypeChange(){
  toggleSection('study_type', { college: 'college_section', university: 'university_section' });
  onUnivLevelChange(); // Reset inner university section
}
function onUnivLevelChange(){
  toggleSection('univ_level', { ug: 'ug_section', pg: 'pg_section' });
}
function computePercentage(totalId, obtainedId, displayId, label){
  const total = parseFloat(qs(totalId).value) || 0;
  const obt = parseFloat(qs(obtainedId).value) || 0;
  const display = qs(displayId);
  if(total > 0 && obt >= 0 && obt <= total){
    const perc = (obt / total) * 100;
    display.innerText = `${label} Percentage: ${perc.toFixed(2)}%`;
    display.style.color = 'green';
  } else {
    display.innerText = obt > total ? 'Obtained marks cannot exceed total marks.' : (total <= 0 ? '' : 'Please enter valid marks.');
    display.style.color = 'red';
  }
}
function displayCGPA(){
  const cgpa = parseFloat(qs('ug_cgpa').value);
  if(!isNaN(cgpa) && cgpa >= 0 && cgpa <= 10) {
    qs('ug_cgpa_display').innerText = `UG CGPA: ${cgpa.toFixed(2)} / 10`;
    qs('ug_cgpa_display').style.color = 'green';
  } else {
    qs('ug_cgpa_display').innerText = 'Please enter a valid CGPA between 0 and 10.';
    qs('ug_cgpa_display').style.color = 'red';
  }
}
function computeTotalAmount(){
  const years = parseInt(qs('loan_years').value) || 0;
  const fee = parseFloat(qs('college_fee').value) || 0;
  const total = years * fee;
  qs('total_amount_display').innerText = 'Total required amount: INR ' + total.toLocaleString();
  return total;
}
async function submitForm(){
  const requiredFields = ['student_name', 'email', 'phone', 'aadhaar', 'family_income', 'study_type'];
  for (const field of requiredFields) {
      if (!qs(field).value) {
          alert(`Please fill the required field: ${field.replace(/_/g, ' ')}`);
          return;
      }
  }
  const payload = {
    student_name: qs('student_name').value, email: qs('email').value, phone: qs('phone').value,
    aadhaar: qs('aadhaar').value, father_name: qs('father_name').value, father_phone: qs('father_phone').value,
    mother_name: qs('mother_name').value, mother_phone: qs('mother_phone').value,
    family_income: qs('family_income').value, study_type: qs('study_type').value,
    univ_level: qs('univ_level').value, t10_total: qs('t10_total').value, t10_obtained: qs('t10_obtained').value,
    t12_total: qs('t12_total').value, t12_obtained: qs('t12_obtained').value, ug_cgpa: qs('ug_cgpa').value,
    loan_years: qs('loan_years').value, college_fee: qs('college_fee').value
  };
  const loader = qs('form-loader');
  const button = loader.parentElement;
  loader.classList.remove('hidden');
  button.disabled = true;
  try{
    const resp = await fetch('/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if(!resp.ok){
      const err = await resp.json();
      // NEW: Handle authorization error
      if (resp.status === 401) {
        alert('Error: ' + (err.error || 'You must be logged in. Please log out and log back in.'));
      } else {
        throw new Error(err.error || resp.statusText);
      }
    } else {
        const data = await resp.json();
        showRecommendations(data);
    }
  } catch(e){
    alert('Error: ' + e.message);
  } finally {
    loader.classList.add('hidden');
    button.disabled = false;
  }
}
//
// Replace the functions 'showRecommendations' and 'applyForLoan' in your script.js
// The rest of the file is unchanged.
//

function showRecommendations(data){
  qs('results_section').classList.remove('hidden');
  const ul = qs('banks_list');
  const status = qs('rec_status');
  const total = data.total_amount || 0;
  const banks = data.recommended_banks || [];
  
  ul.innerHTML = '';
  status.innerHTML = `Found <strong>${banks.length}</strong> loan options for your requested amount of <strong>INR ${total.toLocaleString()}</strong>.`;

  if (banks.length === 0) {
    status.innerHTML += "<br>Unfortunately, no banks matched your profile. Please try adjusting the loan amount or other criteria.";
    qs('emi_calculator').classList.add('hidden');
    return;
  }
  
  banks.forEach(b => {
    const li = document.createElement('li');
    // We still need this to pass the bank data to the 'applyForLoan' (save) function
    const safeBank = JSON.stringify(b).replace(/'/g, "\\'");
    
    // (!!!) CHANGED (!!!) - Updated button layout
    li.innerHTML = `
      <div class="bank-details">
        <strong>${b.name}</strong>
        <span>${b.package} &bull; Interest: <strong>${b.interest_rate}%</strong></span>
      </div>
      <div class="bank-actions">
          <button class="btn btn-secondary" onclick="setupEMICalculator(${total}, ${b.interest_rate})">Calculate EMI</button>
          
          <button class="btn btn-secondary" onclick='applyForLoan(${safeBank}, this)'>
            <i class="fas fa-save"></i> Save Application
          </button>
          
          <a href="${b.url}" target="_blank" class="btn btn-apply">
            Apply at Bank <i class="fas fa-external-link-alt"></i>
          </a>
      </div>
    `;
    ul.appendChild(li);
  });
}


// --- MODIFIED: applyForLoan ---
// This function is now just for 'Saving' the application, not redirecting.
async function applyForLoan(bankDetails, buttonElement) {
    
    buttonElement.disabled = true;
    buttonElement.innerHTML = 'Saving...';
    
    const payload = {
        bank_name: bankDetails.name, 
        loan_package: bankDetails.package
    };
    
    try {
        const resp = await fetch('/apply', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await resp.json();
        
        if (!resp.ok) { 
            throw new Error(result.error || 'Unknown server error.'); 
        }

        // (!!!) CHANGED (!!!) - This is the "Done" state.
        buttonElement.innerHTML = '<i class="fas fa-check"></i> Saved!';
        
    } catch (e) {
        alert('Application Failed: ' + e.message);
        buttonElement.disabled = false; // Re-enable if there was a failure
        buttonElement.innerHTML = '<i class="fas fa-save"></i> Save Application';
    }
}
// ... (setupEMICalculator, calculateEMI, toggleChatWindow, clearChatHistory, displayWelcomeMessage, addMessage, scrollChatToBottom, sendChatMessage, and all Voice functions are unchanged) ...
function setupEMICalculator(amount, interest) {
    qs('emi_calculator').classList.remove('hidden');
    qs('emi_amount').value = amount;
    qs('emi_interest').value = interest;
    qs('emi_tenure').value = qs('loan_years').value;
    qs('emi_result').innerText = '';
    qs('emi_calculator').scrollIntoView({ behavior: 'smooth' });
}
function calculateEMI() {
    const P = parseFloat(qs('emi_amount').value);
    const annual_r = parseFloat(qs('emi_interest').value);
    const N = parseFloat(qs('emi_tenure').value);
    if (isNaN(P) || isNaN(annual_r) || isNaN(N) || P <= 0 || annual_r <= 0 || N <= 0) {
        qs('emi_result').innerText = 'Please enter valid numbers for all fields.';
        return;
    }
    const r = (annual_r / 12) / 100;
    const n = N * 12;
    const emi = P * r * (Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
    qs('emi_result').innerText = `Your estimated monthly payment is INR ${emi.toLocaleString('en-IN', { maximumFractionDigits: 0 })} for ${N} years.`;
}
function toggleChatWindow() {
    const chatWindow = qs('chat-window');
    const chatMessages = qs('chat-messages');
    chatWindow.classList.toggle('hidden');
    if (!chatWindow.classList.contains('hidden')) {
        if (chatMessages.children.length === 0) {
            displayWelcomeMessage();
        }
        scrollChatToBottom();
        qs('chat-input-text').focus();
    }
}
function clearChatHistory() {
    const chatMessages = qs('chat-messages');
    chatMessages.innerHTML = '';
    displayWelcomeMessage();
}
function displayWelcomeMessage() {
    const botResponse = "Hello! I'm your **Student Loan Assistant**. Ask me anything about Indian student loans and the application process. Type 'help' to start."
    addMessage(botResponse, 'bot');
    speakResponse("Hello! I'm your Student Loan Assistant. Ask me anything about Indian student loans and the application process. Type help to start.");
}
function addMessage(text, sender) {
    const chatMessages = qs('chat-messages');
    const msgDiv = document.createElement('div');
    msgDiv.classList.add('chat-message', `${sender}-message`);
    const formattedText = text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    msgDiv.innerHTML = `<div class="message-bubble">${formattedText}</div>`;
    chatMessages.appendChild(msgDiv);
    scrollChatToBottom();
}
function scrollChatToBottom() {
    const chatMessages = qs('chat-messages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
async function sendChatMessage() {
    const inputText = qs('chat-input-text');
    const userMessage = inputText.value.trim();
    if (userMessage === '') return;
    if (userMessage.toLowerCase() === 'clear' || userMessage.toLowerCase() === 'clear all') {
        addMessage(userMessage, 'user');
        inputText.value = '';
        clearChatHistory();
        return;
    }
    addMessage(userMessage, 'user');
    inputText.value = '';
    try {
        qs('chat-input-text').disabled = true;
        qs('send-chat-btn').disabled = true;
        qs('voice-btn').disabled = true;
        const resp = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: userMessage })
        });
        if (!resp.ok) {
            throw new Error('Failed to get bot response.');
        }
        const data = await resp.json();
        const botResponse = data.response;
        addMessage(botResponse, 'bot');
        speakResponse(botResponse);
    } catch (e) {
        console.error("Chatbot Error:", e);
        addMessage("Sorry, I'm having trouble connecting to the AI right now. Please check your internet connection and try again.", 'bot');
    } finally {
        qs('chat-input-text').disabled = false;
        qs('send-chat-btn').disabled = false;
        qs('voice-btn').disabled = false;
        qs('chat-input-text').focus();
    }
}
let recognition = null;
let isRecording = false;
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = function() {
        isRecording = true;
        qs('voice-btn').classList.add('recording');
        qs('voice-btn').innerHTML = '<i class="fas fa-stop"></i>';
        qs('chat-input-text').placeholder = 'Listening... Speak now.';
    };
    recognition.onresult = function(event) {
        const transcript = event.results[0][0].transcript;
        qs('chat-input-text').value = transcript;
        sendChatMessage();
    };
    recognition.onerror = function(event) {
        console.error('Speech recognition error', event);
        if (event.error !== 'no-speech') {
            addMessage(`Voice Error: ${event.error}. Please check microphone permissions.`, 'bot');
        } 
        stopRecordingState();
    };
    recognition.onend = function() {
        stopRecordingState();
    };
} else {
    qs('voice-btn').style.display = 'none';
    console.warn("Web Speech API not supported in this browser. Voice assistant disabled.");
}
function stopRecordingState() {
    isRecording = false;
    qs('voice-btn').classList.remove('recording');
    qs('voice-btn').innerHTML = '<i class="fas fa-microphone"></i>';
    qs('chat-input-text').placeholder = 'Ask a question...';
}
function toggleVoiceInput() {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch (e) {
            console.error("Could not start recognition:", e);
            stopRecordingState();
        }
    }
}
function speakResponse(text) {
    const synth = window.speechSynthesis;
    if (!synth || synth.speaking) return;
    const utterThis = new SpeechSynthesisUtterance(text.replace(/\*\*(.*?)\*\*/g, '$1'));
    utterThis.pitch = 1.0;
    utterThis.rate = 1.0; 
    synth.speak(utterThis);
}

// MODIFIED: DOMContentLoaded listener
document.addEventListener('DOMContentLoaded', () => {
  onStudyTypeChange();
  
  // Chatbot event listeners
  qs('chat-toggle-btn').addEventListener('click', toggleChatWindow);
  qs('close-chat-btn').addEventListener('click', toggleChatWindow);
  qs('voice-btn').addEventListener('click', toggleVoiceInput);
  
  qs('chat-messages').innerHTML = '';
  
  // NOTE: The new 'checkSession()' function is now called from the
  // <script> block in index.html, so it's removed from here.
});