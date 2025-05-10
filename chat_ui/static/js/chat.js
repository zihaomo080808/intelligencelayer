// AI Recommender Simulator
document.addEventListener('DOMContentLoaded', function() {
    // DOM elements - General
    const tabs = document.querySelectorAll('.tab');
    const tabContents = document.querySelectorAll('.tab-content');
    const settingsButton = document.getElementById('settings-button');
    const settingsModal = document.getElementById('settings-modal');
    const closeModal = document.querySelector('.close');
    const saveSettings = document.getElementById('save-settings');
    const displayedUserId = document.getElementById('displayed-user-id');
    
    // DOM elements - Chat
    const chatMessages = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    
    // DOM elements - Profile
    const profileBio = document.getElementById('profile-bio');
    const profileLocation = document.getElementById('profile-location');
    const newInterest = document.getElementById('new-interest');
    const updateProfileButton = document.getElementById('update-profile');
    
    // DOM elements - Recommendations
    const likeButtons = document.querySelectorAll('.like-button');
    const skipButtons = document.querySelectorAll('.skip-button');
    const chatButtons = document.querySelectorAll('.chat-button');
    
    // App configuration
    let appConfig = {
        userId: document.getElementById('user-id').value,
        itemId: document.getElementById('item-id').value,
        apiUrl: document.getElementById('api-url').value,
        opportunity: {
            title: document.getElementById('opportunity-title').value,
            description: document.getElementById('opportunity-desc').value,
            date: document.getElementById('opportunity-date').value,
            location: document.getElementById('opportunity-location').value
        }
    };
    
    // Update displayed user ID
    displayedUserId.textContent = appConfig.userId;
    
    // Track if user has selected a recommendation to chat about
    let hasSelectedRecommendation = false;

    // Tab switching
    function switchTab(tabId) {
        // If trying to access chat before selecting a recommendation, redirect to recommendations
        if (tabId === 'chat' && !hasSelectedRecommendation) {
            // Show a message instructing the user to select a recommendation first
            const toast = document.createElement('div');
            toast.className = 'toast-message';
            toast.textContent = 'Please select a recommendation to chat about first!';
            document.body.appendChild(toast);

            // Remove the toast after a delay
            setTimeout(() => {
                toast.remove();
            }, 3000);

            // Switch to recommendations tab instead
            tabId = 'recommendations';
        }

        // Remove active class from all tabs and contents
        tabs.forEach(tab => tab.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // Add active class to selected tab and content
        const selectedTab = document.querySelector(`.tab[data-tab="${tabId}"]`);
        const selectedContent = document.getElementById(`${tabId}-tab`);

        if (selectedTab && selectedContent) {
            selectedTab.classList.add('active');
            selectedContent.classList.add('active');

            // If switching to chat tab, focus on message input
            if (tabId === 'chat' && messageInput) {
                setTimeout(() => messageInput.focus(), 100);
            }
        }
    }
    
    // Tab click event
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
    
    // === Chat functionality ===
    
    // Scroll to bottom of chat
    function scrollToBottom() {
        if (chatMessages) {
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
    }

    // Format current time
    function getTimeString() {
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        
        hours = hours % 12;
        hours = hours ? hours : 12; // Convert 0 to 12
        
        return `${hours}:${minutes} ${ampm}`;
    }

    // Add a message to the chat
    function addMessage(message, isUser = false) {
        if (!chatMessages) return;
        
        const messageRow = document.createElement('div');
        messageRow.className = `message-row ${isUser ? 'user-row' : ''}`;

        const messageElement = document.createElement('div');
        messageElement.className = `message ${isUser ? 'user-message' : 'agent-message'}`;
        messageElement.textContent = message;

        const timeElement = document.createElement('div');
        timeElement.className = `time ${isUser ? 'user-time' : 'agent-time'}`;
        timeElement.textContent = getTimeString();

        messageRow.appendChild(messageElement);
        messageRow.appendChild(timeElement);
        chatMessages.appendChild(messageRow);

        scrollToBottom();
    }

    // Show typing indicator
    function showTypingIndicator() {
        if (!chatMessages) return;
        
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('span');
            indicator.appendChild(dot);
        }
        
        chatMessages.appendChild(indicator);
        scrollToBottom();
    }

    // Hide typing indicator
    function hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // Function to handle API errors
    function handleApiError() {
        addMessage("Sorry, I couldn't connect to the server. Please try again in a moment.");
    }

    // Send a message to the API and get a response
    async function sendMessage(message) {
        if (!messageInput || !sendButton) return;

        // Disable input while sending
        messageInput.disabled = true;
        sendButton.disabled = true;

        try {
            // Show typing indicator
            showTypingIndicator();

            const opportunityDetails = {
                id: appConfig.itemId,
                title: appConfig.opportunity.title,
                description: appConfig.opportunity.description,
                date: appConfig.opportunity.date,
                location: appConfig.opportunity.location
            };

            // Debug log for message
            console.log("User message:", message);
            console.log("Opportunity details:", opportunityDetails);

            // Prepare the API request
            // Get the API URL from the config, or use a default
            const apiBaseUrl = window.location.origin;  // Use the current origin (proxy server)

            // Parse the API URL to determine which endpoint to use
            let endpoint = `${apiBaseUrl}/api/conversation`;

            // Debug log for API endpoint
            console.log("Using API endpoint:", endpoint);

            // Make the actual API call with automatic fallback
            try {
                // Prepare request options
                const requestOptions = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        user_id: appConfig.userId,
                        item_id: opportunityDetails.id,
                        message: message,
                        context: {
                            title: opportunityDetails.title,
                            description: opportunityDetails.description,
                            date: opportunityDetails.date,
                            location: opportunityDetails.location
                        }
                    })
                };

                // First try the primary endpoint
                console.log(`Trying API endpoint: ${endpoint}`);
                let response;

                try {
                    response = await fetch(endpoint, requestOptions);
                    console.log("Response status:", response.status);
                } catch (primaryError) {
                    console.warn(`Primary API endpoint failed: ${primaryError.message}`);
                    // Try the fallback endpoint
                    const fallbackEndpoint = `${apiBaseUrl}/twilio/feedback/chat`;
                    console.log(`Trying fallback API endpoint: ${fallbackEndpoint}`);
                    try {
                        response = await fetch(fallbackEndpoint, requestOptions);
                        console.log("Fallback response status:", response.status);
                    } catch (fallbackError) {
                        console.error("Fallback endpoint also failed:", fallbackError);
                        throw new Error("Both API endpoints failed");
                    }
                }

                // Check if the request was successful
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    console.error("API error:", response.status, errorData);
                    throw new Error(`API error: ${response.status}`);
                }

                // Parse the response
                const data = await response.json();
                console.log("API response:", data);

                // Hide typing indicator
                hideTypingIndicator();

                // Check which endpoint we're using and extract the response accordingly
                let messageText = null;

                // Handle twilio endpoint format (/twilio/feedback/chat)
                if (data && data.agent_response) {
                    messageText = data.agent_response;
                    console.log("Found agent_response in data");
                }
                // Handle our new endpoint format (/api/conversation)
                else if (data && data.response) {
                    messageText = data.response;
                    console.log("Found response in data");
                }

                if (messageText) {
                    addMessage(messageText);
                } else {
                    console.error("Could not find response in data:", data);
                    throw new Error("Invalid response format");
                }
            } catch (apiError) {
                console.error("API call failed:", apiError);
                hideTypingIndicator();

                // Fallback to simulation mode only when API fails
                console.warn("Falling back to simulation mode due to API error");

                // Generate a fallback response
                let fallbackResponse = "";

                // Simple keyword matching as a fallback
                if (message.toLowerCase().includes("where") || message.toLowerCase().includes("location")) {
                    fallbackResponse = `The ${opportunityDetails.title} will be held at ${opportunityDetails.location || 'a location TBD'}. It's gonna be lit! Are you planning to attend?`;
                }
                else if (message.toLowerCase().includes("when") || message.toLowerCase().includes("date") || message.toLowerCase().includes("time")) {
                    fallbackResponse = `${opportunityDetails.title} is happening on ${opportunityDetails.date || 'a date to be announced'}. Make sure to mark your calendar! Need any other details?`;
                }
                else if (message.toLowerCase().includes("cost") || message.toLowerCase().includes("price") || message.toLowerCase().includes("fee")) {
                    fallbackResponse = `Good news! ${opportunityDetails.title} is likely free to attend. Just bring your laptop and ideas!`;
                }
                else {
                    // Generic responses for anything else
                    const genericResponses = [
                        `${opportunityDetails.title} sounds perfect for you! ${opportunityDetails.description} What specific part are you most interested in?`,
                        `I'm sure ${opportunityDetails.title} will be an amazing opportunity to network and learn. What else do you want to know?`,
                        `${opportunityDetails.title} is definitely worth checking out! Any specific questions?`,
                        `I think ${opportunityDetails.title} would be a great fit for you! Anything specific you're curious about?`
                    ];
                    fallbackResponse = genericResponses[Math.floor(Math.random() * genericResponses.length)];
                }

                addMessage(fallbackResponse + " (Note: This is a simulated response because the API is currently unavailable)");
            }

        } catch (error) {
            console.error("Error in message handling:", error);
            hideTypingIndicator();
            // Fallback for network or API errors
            handleApiError();
        } finally {
            // Re-enable input
            messageInput.disabled = false;
            sendButton.disabled = false;
            messageInput.focus();
        }
    }

    // Handle send button click
    function handleSend() {
        if (!messageInput) return;
        
        const message = messageInput.value.trim();
        if (message) {
            addMessage(message, true);
            messageInput.value = '';
            sendMessage(message);
        }
    }
    
    // === Profile functionality ===
    
    // Update profile
    async function updateProfile() {
        const bio = profileBio.value.trim();
        const location = profileLocation.value.trim();
        const interests = Array.from(document.querySelectorAll('.interest-tag')).map(tag => 
            tag.textContent.replace(' ×', '')
        );
        
        if (!bio) {
            alert('Please enter a bio to create your profile');
            return;
        }
        
        // Simulate profile update with embedding generation
        updateProfileButton.textContent = 'Generating embedding...';
        updateProfileButton.disabled = true;
        
        // Simulate API call with a delay
        setTimeout(() => {
            // Update embedding visualization with random values
            const embedVector = document.querySelector('.embedding-vector');
            const randomEmbedding = Array.from({length: 10}, () => (Math.random() * 0.9 + 0.1).toFixed(2));
            embedVector.textContent = `[${randomEmbedding.join(', ')}, ..., ${(Math.random() * 0.9 + 0.1).toFixed(2)}]`;
            
            // Update dominant topics based on interests
            const topicValue = document.querySelector('.stat-value:last-child');
            const topicsText = interests.map(interest => 
                `${interest} (${(Math.random() * 0.5 + 0.5).toFixed(2)})`
            ).slice(0, 2).join(', ');
            topicValue.textContent = topicsText || 'Technology (0.78), Education (0.65)';
            
            // Switch to recommendations tab
            switchTab('recommendations');
            
            // Reset button
            updateProfileButton.textContent = 'Update Profile';
            updateProfileButton.disabled = false;
        }, 1500);
    }
    
    // Add new interest tag
    function addInterestTag(interest) {
        if (!interest) return;
        
        const interestTags = document.querySelector('.interest-tags');
        const tag = document.createElement('span');
        tag.className = 'interest-tag';
        tag.innerHTML = `${interest} <i class="fas fa-times"></i>`;
        
        // Add remove functionality
        tag.querySelector('i').addEventListener('click', function() {
            tag.remove();
        });
        
        // Insert before the input
        interestTags.insertBefore(tag, newInterest);
    }
    
    // === Recommendation functionality ===
    
    // Handle recommendation actions
    function handleRecommendationAction(action, id) {
        const card = document.querySelector(`.recommendation-card [data-id="${id}"]`).closest('.recommendation-card');
        
        switch(action) {
            case 'like':
                // Visual feedback
                card.style.borderColor = '#4CAF50';
                setTimeout(() => {
                    card.style.borderColor = '';
                }, 1000);
                
                // Add to feedback history
                const feedbackItems = document.querySelector('.feedback-items');
                if (feedbackItems) {
                    const title = card.querySelector('h3').textContent;
                    const feedbackItem = document.createElement('div');
                    feedbackItem.className = 'feedback-item liked';
                    feedbackItem.innerHTML = `
                        <div class="feedback-item-header">
                            <span class="feedback-title">${title}</span>
                            <span class="feedback-type">Liked</span>
                        </div>
                        <div class="feedback-date">Just now</div>
                    `;
                    feedbackItems.prepend(feedbackItem);
                }
                
                // Update Rocchio visualization
                const currentPoint = document.getElementById('current-point');
                if (currentPoint) {
                    currentPoint.style.left = '65%';
                    currentPoint.style.top = '25%';
                }
                break;
                
            case 'skip':
                // Visual feedback
                card.style.borderColor = '#f44336';
                setTimeout(() => {
                    card.style.borderColor = '';
                }, 1000);
                
                // Add to feedback history
                const skipItems = document.querySelector('.feedback-items');
                if (skipItems) {
                    const title = card.querySelector('h3').textContent;
                    const feedbackItem = document.createElement('div');
                    feedbackItem.className = 'feedback-item skipped';
                    feedbackItem.innerHTML = `
                        <div class="feedback-item-header">
                            <span class="feedback-title">${title}</span>
                            <span class="feedback-type">Skipped</span>
                        </div>
                        <div class="feedback-date">Just now</div>
                    `;
                    skipItems.prepend(feedbackItem);
                }
                
                // Update Rocchio visualization
                const skipPoint = document.getElementById('current-point');
                if (skipPoint) {
                    skipPoint.style.left = '40%';
                    skipPoint.style.top = '40%';
                }
                break;
                
            case 'chat':
                // Set flag indicating user has selected a recommendation
                hasSelectedRecommendation = true;

                // Switch to chat tab and populate title in chat
                switchTab('chat');

                // Extract opportunity details
                const title = card.querySelector('h3').textContent;
                const desc = card.querySelector('.recommendation-desc').textContent;

                // Extract additional metadata if available
                let date = '';
                let location = '';
                try {
                    date = card.querySelector('.meta-item:first-child span').textContent;
                    location = card.querySelector('.meta-item:last-child span').textContent;
                } catch (e) {
                    console.warn('Could not extract metadata from card', e);
                }

                // Update app config with current opportunity
                appConfig.itemId = id;
                appConfig.opportunity.title = title;
                appConfig.opportunity.description = desc;
                if (date) appConfig.opportunity.date = date;
                if (location) appConfig.opportunity.location = location;

                // Clear any existing messages and add a welcome message about this opportunity
                chatMessages.innerHTML = '';
                
                // Use casual style matching generator.py
                const casualGreetings = [
                    `Yo, so you're into ${title}? Nice choice!`,
                    `Look at you checking out ${title}! What do you wanna know?`,
                    `${title} is fire! What's up?`,
                    `Totally digging your interest in ${title}! Questions?`
                ];
                
                // Choose a random greeting
                addMessage(casualGreetings[Math.floor(Math.random() * casualGreetings.length)]);

                break;
        }
    }
    
    // === Settings modal functionality ===
    
    function openSettingsModal() {
        if (!settingsModal) return;
        
        settingsModal.style.display = 'block';
        
        // Load current settings
        document.getElementById('user-id').value = appConfig.userId;
        document.getElementById('item-id').value = appConfig.itemId;
        document.getElementById('api-url').value = appConfig.apiUrl;
        document.getElementById('opportunity-title').value = appConfig.opportunity.title;
        document.getElementById('opportunity-desc').value = appConfig.opportunity.description;
        document.getElementById('opportunity-date').value = appConfig.opportunity.date;
        document.getElementById('opportunity-location').value = appConfig.opportunity.location;
    }
    
    function closeSettingsModal() {
        if (!settingsModal) return;
        settingsModal.style.display = 'none';
    }
    
    function saveSettingsConfig() {
        appConfig = {
            userId: document.getElementById('user-id').value,
            itemId: document.getElementById('item-id').value,
            apiUrl: document.getElementById('api-url').value,
            opportunity: {
                title: document.getElementById('opportunity-title').value,
                description: document.getElementById('opportunity-desc').value,
                date: document.getElementById('opportunity-date').value,
                location: document.getElementById('opportunity-location').value
            }
        };
        
        // Update displayed user ID
        displayedUserId.textContent = appConfig.userId;
        
        closeSettingsModal();
    }
    
    // === Event Listeners ===
    
    // Chat event listeners
    if (sendButton) {
        sendButton.addEventListener('click', handleSend);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                handleSend();
            }
        });
    }
    
    // Profile event listeners
    if (updateProfileButton) {
        updateProfileButton.addEventListener('click', updateProfile);
    }
    
    if (newInterest) {
        newInterest.addEventListener('keypress', function(event) {
            if (event.key === 'Enter' && this.value.trim()) {
                addInterestTag(this.value.trim());
                this.value = '';
            }
        });
    }
    
    // Recommendation action event listeners
    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            handleRecommendationAction('like', this.getAttribute('data-id'));
        });
    });
    
    skipButtons.forEach(button => {
        button.addEventListener('click', function() {
            handleRecommendationAction('skip', this.getAttribute('data-id'));
        });
    });
    
    chatButtons.forEach(button => {
        button.addEventListener('click', function() {
            handleRecommendationAction('chat', this.getAttribute('data-id'));
        });
    });
    
    // Settings modal event listeners
    if (settingsButton) {
        settingsButton.addEventListener('click', openSettingsModal);
    }
    
    if (closeModal) {
        closeModal.addEventListener('click', closeSettingsModal);
    }
    
    if (saveSettings) {
        saveSettings.addEventListener('click', saveSettingsConfig);
    }
    
    // Close modal if clicked outside content
    window.addEventListener('click', function(event) {
        if (event.target === settingsModal) {
            closeSettingsModal();
        }
    });
    
    // Initial setup
    scrollToBottom();

    // Add initial interest tags click handlers
    document.querySelectorAll('.interest-tag').forEach(tag => {
        tag.querySelector('i').addEventListener('click', function() {
            tag.remove();
        });
    });

    // Fetch recommendation and show as first message in chat
    async function fetchRecommendation() {
        try {
            // Show typing indicator while fetching recommendation
            showTypingIndicator();

            const response = await fetch(`http://localhost:8000/api/recommend/${appConfig.userId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error(`API error: ${response.status}`);
            }

            const data = await response.json();
            hideTypingIndicator();

            // Clear existing welcome message
            if (chatMessages) {
                chatMessages.innerHTML = '';

                // Add the recommendation as the first message
                addMessage(data.recommendations);

                // Set recommendation received flag
                hasSelectedRecommendation = true;
                
                // Set item details for future conversation agent interactions
                console.log("Parsing recommendation:", data.recommendations);

                try {
                    // Better regex for different formats of recommendations
                    // This should handle formats like "Found this. You're in San Francisco right, look at this: AI for Good Hackathon: A virtual hackathon..."
                    const cleanedRec = data.recommendations.replace(/^Found this\.\s*You're in [^,]+,\s*/, '');
                    console.log("Cleaned recommendation:", cleanedRec);

                    // Try to match the core recommendation
                    let oppMatch = cleanedRec.match(/look at this:\s*(.*?):\s*(.*?)(\(https?:\/\/[^)]+\))/i);

                    // If that fails, try a simpler pattern
                    if (!oppMatch) {
                        oppMatch = cleanedRec.match(/(.*?):\s*(.*?)(\(https?:\/\/[^)]+\))/i);
                    }

                    // Extra fallback - find just the title and URL
                    if (!oppMatch) {
                        const titleMatch = cleanedRec.match(/([^.:]+Hackathon|Conference|Workshop|Bootcamp|Meetup[^.:]*)/i);
                        if (titleMatch) {
                            const title = titleMatch[1].trim();
                            const descStart = cleanedRec.indexOf(title) + title.length;
                            const descEnd = cleanedRec.indexOf('(http');

                            if (descEnd > descStart) {
                                const description = cleanedRec.substring(descStart, descEnd).replace(/^[:\s]+/, '').trim();

                                appConfig.opportunity.title = title;
                                appConfig.opportunity.description = description;
                            } else {
                                appConfig.opportunity.title = title;
                                appConfig.opportunity.description = "An exciting opportunity in tech.";
                            }
                        }
                    } else if (oppMatch && oppMatch.length >= 3) {
                        const title = oppMatch[1].trim();
                        const description = oppMatch[2].trim();

                        // Update app config with extracted opportunity details
                        appConfig.opportunity.title = title;
                        appConfig.opportunity.description = description;
                    }

                    // Generate a random ID if none is set
                    if (!appConfig.itemId || appConfig.itemId === 'opportunity_456') {
                        appConfig.itemId = 'opp_' + Math.floor(Math.random() * 1000);
                    }

                    console.log("Extracted opportunity details:", {
                        title: appConfig.opportunity.title,
                        description: appConfig.opportunity.description
                    });
                } catch (parseError) {
                    console.error("Error parsing recommendation:", parseError);
                    // Fallback to a default title
                    appConfig.opportunity.title = "AI Hackathon";
                    appConfig.opportunity.description = "A virtual hackathon focused on AI solutions.";
                }
            }
        } catch (error) {
            console.error("Error fetching recommendation:", error);
            hideTypingIndicator();
            // If error, add a default message
            if (chatMessages && chatMessages.innerHTML === '') {
                const defaultRecs = [
                    "AI for Good Hackathon: A virtual hackathon focused on developing AI solutions for social impact challenges. (https://example.com/ai-hackathon)",
                    "Machine Learning Conference: Annual conference on machine learning and AI technologies. (https://example.com/ml-conference)",
                    "Data Science Bootcamp: Intensive training program for data science professionals. (https://example.com/ds-bootcamp)"
                ];

                // Choose a random recommendation
                const randomIndex = Math.floor(Math.random() * defaultRecs.length);
                const rec = defaultRecs[randomIndex];

                // Add a prefix that matches generator.py's style
                const prefixes = [
                    "Yo, check this out!",
                    "This would be perfect for you!",
                    "Found something awesome!",
                    "You might be interested in this:"
                ];
                const prefix = prefixes[Math.floor(Math.random() * prefixes.length)];

                // Create the full message
                const fullMessage = `${prefix}\n\n${rec}`;
                addMessage(fullMessage);

                // Set flag to enable conversation
                hasSelectedRecommendation = true;

                // Extract title and description
                const titleEndPos = rec.indexOf(': ');
                if (titleEndPos > 0) {
                    const title = rec.substring(0, titleEndPos);
                    const description = rec.substring(titleEndPos + 2).split(' (https')[0];

                    // Set the opportunity details
                    appConfig.opportunity.title = title;
                    appConfig.opportunity.description = description;

                    // Set a default ID
                    appConfig.itemId = 'opp_' + Math.floor(Math.random() * 1000);

                    // Log what we extracted
                    console.log("Set default opportunity:", {
                        title: title,
                        description: description,
                        id: appConfig.itemId
                    });
                }
            }
        }
    }

    // Fetch recommendation when the page loads
    fetchRecommendation();

    // When the page loads, start with the profile tab
    // On profile update, move to recommendations tab
    // Chat tab now has initial recommendations from the API
});