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
    const recommendButton = document.getElementById('recommend-button');
    
    // DOM elements - Profile
    const profileBio = document.getElementById('profile-bio');
    const profileLocation = document.getElementById('profile-location');
    const newInterest = document.getElementById('new-interest');
    const updateProfileButton = document.getElementById('update-profile');
    
    // DOM elements - Recommendations
    const likeButtons = document.querySelectorAll('.like-button');
    const skipButtons = document.querySelectorAll('.skip-button');
    
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
        },
        userOnboarded: false,
        userProfile: {
            name: "",
            location: "",
            education: "",
            occupation: "",
            current_projects: [],
            interests: [],
            skills: [],
            goals: [],
            bio: ""
        },
        onboardingStep: 0,
        maxOnboardingAttempts: 3,  // Number of attempts before auto-completing
        onboardingAttempts: 0,
        useIntelligentOnboarding: true // Flag to use the new API-based onboarding
    };
    
    // Update displayed user ID
    displayedUserId.textContent = appConfig.userId;

    // Always allow direct chat access
    let hasSelectedRecommendation = true;

    // Tab switching
    function switchTab(tabId) {
        // Remove active class from all tabs and contents
        tabs.forEach(tab => tab.classList.remove('active'));
        tabContents.forEach(content => content.classList.remove('active'));

        // Add active class to selected tab and content
        const selectedTab = document.querySelector(`.tab[data-tab="${tabId}"]`);
        const selectedContent = document.getElementById(`${tabId}-tab`);

        if (selectedTab && selectedContent) {
            selectedTab.classList.add('active');
            selectedContent.classList.add('active');

            // If switching to chat tab
            if (tabId === 'chat') {
                // Check for saved profile first
                const savedProfile = localStorage.getItem('userProfile');

                if (savedProfile) {
                    // If we have a saved profile, load it
                    appConfig.userProfile = JSON.parse(savedProfile);
                    appConfig.userOnboarded = true;
                }

                // Focus on message input regardless of onboarding status
                if (messageInput) {
                    setTimeout(() => messageInput.focus(), 100);
                }

                // Make sure the chat is blank if not onboarded and no messages yet
                if (!appConfig.userOnboarded && chatMessages && chatMessages.children.length === 0) {
                    // Ensure the chat is empty - don't add any starting messages
                    chatMessages.innerHTML = '';
                }
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

    // Onboarding questions
    const onboardingQuestions = [
        "Hey there! 👋 I'm the onboarding assistant. What's your name?",
        "Nice to meet you, {name}! Where are you located, where have you studied, and what are you currently doing?",
        "What are your top interests and skills? (Feel free to list several)"
    ];

    // Handle onboarding process with intelligent API-based parsing
    async function handleOnboarding(message) {
        // Track attempts for fallback handling
        appConfig.onboardingAttempts++;

        // Show typing indicator while processing
        showTypingIndicator();

        try {
            if (appConfig.useIntelligentOnboarding) {
                // Use the intelligent onboarding API
                const apiBaseUrl = window.location.origin;
                const endpoint = `${apiBaseUrl}/api/onboarding/process`;

                console.log(`Processing onboarding message using API (step ${appConfig.onboardingStep})`);

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        step: appConfig.onboardingStep,
                        profile: appConfig.userProfile,
                        user_id: appConfig.userId
                    })
                });

                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }

                const data = await response.json();
                console.log("Onboarding API response:", data);

                // Update user profile with extracted information
                if (data.profile) {
                    appConfig.userProfile = data.profile;
                }

                // Hide typing indicator
                hideTypingIndicator();

                // Move to next step
                appConfig.onboardingStep++;
                appConfig.onboardingAttempts = 0; // Reset attempts

                // Add the next question or complete onboarding
                if (data.complete) {
                    completeOnboarding();
                } else if (data.next_question) {
                    addMessage(data.next_question);
                } else {
                    // Fallback if no next question is provided
                    if (appConfig.onboardingStep <= onboardingQuestions.length) {
                        const nextQuestion = onboardingQuestions[appConfig.onboardingStep];
                        addMessage(nextQuestion.replace('{name}', appConfig.userProfile.name || 'there'));
                    } else {
                        completeOnboarding();
                    }
                }

            } else {
                // Fallback to the original simple onboarding logic
                hideTypingIndicator();

                // Check if we need to auto-complete onboarding due to too many invalid attempts
                if (appConfig.onboardingAttempts > appConfig.maxOnboardingAttempts) {
                    completeOnboarding();
                    return;
                }

                switch(appConfig.onboardingStep) {
                    case 0:
                        // First message, store name
                        if (message.length < 2) {
                            // Handle invalid name
                            addMessage("I didn't quite catch that. Could you share your name again?");
                        } else {
                            appConfig.userProfile.name = message;
                            appConfig.onboardingStep++;
                            appConfig.onboardingAttempts = 0; // Reset attempts counter
                            addMessage(onboardingQuestions[1].replace('{name}', message));
                        }
                        break;

                    case 1:
                        // Second message, store location
                        if (message.length < 2) {
                            // Handle invalid location
                            addMessage("I'm not sure I got that. Could you tell me where you're located?");
                        } else {
                            appConfig.userProfile.location = message;
                            appConfig.onboardingStep++;
                            appConfig.onboardingAttempts = 0; // Reset attempts counter
                            addMessage(onboardingQuestions[2]);
                        }
                        break;

                    case 2:
                        // Third message, store interests
                        if (message.length < 2) {
                            // Use default interests if the user doesn't provide any
                            appConfig.userProfile.interests = ["technology", "events", "networking"];
                        } else {
                            appConfig.userProfile.interests = message.split(',').map(i => i.trim());
                        }

                        // Complete onboarding regardless of response quality
                        completeOnboarding();
                        break;
                }
            }
        } catch (error) {
            console.error("Error in onboarding process:", error);

            // Hide typing indicator
            hideTypingIndicator();

            // Fall back to simple processing if API fails
            appConfig.useIntelligentOnboarding = false;

            // Use a simple approach for this message
            if (appConfig.onboardingStep === 0) {
                // Just extract the first word as a name
                const nameParts = message.split(' ');
                appConfig.userProfile.name = nameParts[0];
                appConfig.onboardingStep++;
                addMessage(onboardingQuestions[1].replace('{name}', nameParts[0]));
            } else if (appConfig.onboardingStep === 1) {
                // Just store the full text as location
                appConfig.userProfile.location = message;
                appConfig.userProfile.bio = message;
                appConfig.onboardingStep++;
                addMessage(onboardingQuestions[2]);
            } else {
                // Just store interests as is
                appConfig.userProfile.interests = message.split(',').map(i => i.trim());
                completeOnboarding();
            }
        }
    }

    // Function to complete onboarding and transition to normal chat
    async function completeOnboarding() {
        // If we have some valid data, update fields
        if (appConfig.userProfile.name) {
            try {
                // Check for bio and embedding
                if (!appConfig.userProfile.bio || !appConfig.userProfile.embedding) {
                    console.log("Fetching additional profile info from Perplexity API...");

                    // Show message about generating bio
                    addMessage("Generating a comprehensive bio based on your profile information...");

                    // Wait 2 seconds to simulate processing
                    await new Promise(resolve => setTimeout(resolve, 2000));

                    // Call the API endpoint to check profile information
                    const apiBaseUrl = window.location.origin;
                    const profileEndpoint = `${apiBaseUrl}/api/onboarding/profile-info/${appConfig.userId}`;

                    try {
                        const response = await fetch(profileEndpoint);
                        if (response.ok) {
                            const profileInfo = await response.json();
                            console.log("Retrieved profile info:", profileInfo);

                            // Check if bio and embedding were generated
                            if (profileInfo.bio_available && profileInfo.embedding_available) {
                                // Add these to the profile (in a real app, the actual data would be returned)
                                appConfig.userProfile.has_enhanced_bio = true;
                                appConfig.userProfile.has_embedding = true;
                            }
                        }
                    } catch (error) {
                        console.error("Error checking profile info:", error);
                    }
                }

                // Save to localStorage
                localStorage.setItem('userProfile', JSON.stringify(appConfig.userProfile));

                // Welcome message with personalization
                addMessage(`Thanks ${appConfig.userProfile.name}! I've got your profile set up with a personalized bio. Alex Hefle will join the conversation once you send your next message.`);

                // Update profile UI elements with expanded profile data
                updateProfileUIFromOnboarding();
            } catch (error) {
                console.error("Error in profile completion:", error);
                // Fallback message
                addMessage(`Thanks ${appConfig.userProfile.name}! I've got your profile set up. Alex Hefle will join the conversation once you send your next message.`);
                updateProfileUIFromOnboarding();
            }
        } else {
            // Complete fallback if we have no valid data at all
            appConfig.userProfile.name = "User";
            addMessage("Great! Your profile is set up. Alex Hefle will join the conversation once you send your next message.");
        }

        // IMPORTANT: Only set the onboarded flag AFTER the final onboarding message is shown
        // This ensures the conversation bot doesn't activate until after this message
        appConfig.userOnboarded = true;
    }

    // Function to update profile UI with extracted information
    function updateProfileUIFromOnboarding() {
        // Update bio with combined information
        if (profileBio) {
            // Check if we have an enhanced bio from Perplexity
            if (appConfig.userProfile.bio && appConfig.userProfile.bio.length > 20) {
                profileBio.value = appConfig.userProfile.bio;

                // Add a subtle indicator that this is AI-enhanced
                const bioHeader = document.querySelector('.form-group label[for="profile-bio"]');
                if (bioHeader && !bioHeader.innerHTML.includes('AI-Enhanced')) {
                    bioHeader.innerHTML += ' <span style="color: #4CAF50; font-size: 12px;">(AI-Enhanced)</span>';
                }
            } else {
                // Fallback to constructing a basic bio
                let bioComponents = [];

                if (appConfig.userProfile.name) {
                    bioComponents.push(`I'm ${appConfig.userProfile.name}`);
                }

                if (appConfig.userProfile.location) {
                    bioComponents.push(`from ${appConfig.userProfile.location}`);
                }

                if (appConfig.userProfile.education) {
                    bioComponents.push(`educated at ${appConfig.userProfile.education}`);
                }

                if (appConfig.userProfile.occupation) {
                    bioComponents.push(`working as ${appConfig.userProfile.occupation}`);
                }

                if (bioComponents.length > 0) {
                    profileBio.value = bioComponents.join(', ');
                }
            }
        }

        // Update location
        if (profileLocation && appConfig.userProfile.location) {
            profileLocation.value = appConfig.userProfile.location;
        }

        // Add all interests and skills
        const tagsToAdd = [];

        // Add interests
        if (appConfig.userProfile.interests && appConfig.userProfile.interests.length > 0) {
            appConfig.userProfile.interests.forEach(interest => {
                if (interest && interest.length > 1) tagsToAdd.push(interest);
            });
        }

        // Add skills
        if (appConfig.userProfile.skills && appConfig.userProfile.skills.length > 0) {
            appConfig.userProfile.skills.forEach(skill => {
                if (skill && skill.length > 1 && !tagsToAdd.includes(skill)) tagsToAdd.push(skill);
            });
        }

        // Clear existing tags first
        const interestTags = document.querySelector('.interest-tags');
        if (interestTags) {
            // Remove all tags except the input
            Array.from(interestTags.querySelectorAll('.interest-tag')).forEach(tag => {
                tag.remove();
            });

            // Add the new tags
            tagsToAdd.forEach(tag => {
                addInterestTag(tag);
            });
        }
    }

    // Function to start onboarding
    function startOnboarding() {
        if (!appConfig.userOnboarded && chatMessages) {
            // Clear any existing messages
            chatMessages.innerHTML = '';

            // Add first onboarding message
            addMessage(onboardingQuestions[0]);
        }
    }

    // Handle send button click
    function handleSend() {
        if (!messageInput) return;

        const message = messageInput.value.trim();
        if (message) {
            // Add the user's message to the chat
            addMessage(message, true);
            messageInput.value = '';

            // Check if the user is still in onboarding process or already onboarded
            if (!appConfig.userOnboarded) {
                // Check if this is the very first message in the chat
                if (chatMessages.children.length === 1) { // Only the user's message is there
                    // Now show the first onboarding question
                    addMessage(onboardingQuestions[0]);
                    // Don't process their first message as an answer yet
                    // We'll wait for their response to the first question
                } else if (chatMessages.children.length >= 3) {
                    // This is a response to our onboarding question, so process it
                    handleOnboarding(message);
                }
            } else {
                // Normal message flow - user is already onboarded
                sendMessage(message);
            }
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
        if (!card) return;

        switch (action) {
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
    
    // Function to fetch and display a recommendation
    async function fetchAndDisplayRecommendation() {
        if (!chatMessages) return;

        // Show loading state
        addMessage("Generating opportunity recommendation for you...");

        // Disable the recommend button during fetch
        if (recommendButton) {
            recommendButton.disabled = true;
            recommendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
        }

        try {
            // Show typing indicator
            showTypingIndicator();

            // Prepare the API request
            const apiBaseUrl = window.location.origin;
            const endpoint = `${apiBaseUrl}/api/recommend`;

            console.log("Requesting recommendation from:", endpoint);

            // Make the API call
            try {
                const requestOptions = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        user_id: appConfig.userId
                    })
                };

                const response = await fetch(endpoint, requestOptions);
                console.log("Response status:", response.status);

                if (!response.ok) {
                    throw new Error(`API error: ${response.status}`);
                }

                // Parse the response
                const data = await response.json();
                console.log("API response:", data);

                // Hide typing indicator
                hideTypingIndicator();

                // Extract recommendation content
                let recommendation = "";

                if (data && data.recommendations) {
                    recommendation = data.recommendations;
                } else if (data && data.response) {
                    recommendation = data.response;
                } else {
                    throw new Error("Invalid response format");
                }

                // Add the recommendation to the chat
                addMessage(recommendation);

                // Set hasSelectedRecommendation to true to allow chatting
                hasSelectedRecommendation = true;

            } catch (apiError) {
                console.error("API call failed:", apiError);
                hideTypingIndicator();

                // Fallback to direct generator.py call if possible
                try {
                    const generatorEndpoint = `${apiBaseUrl}/api/generate`;
                    console.log("Trying fallback generator endpoint:", generatorEndpoint);

                    const fallbackOptions = {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({
                            user_id: appConfig.userId,
                            profile: {
                                stances: ["tech", "startup", "programming"],
                                location: profileLocation ? profileLocation.value : "San Francisco"
                            }
                        })
                    };

                    const fallbackResponse = await fetch(generatorEndpoint, fallbackOptions);

                    if (!fallbackResponse.ok) {
                        throw new Error("Fallback generator API also failed");
                    }

                    const fallbackData = await fallbackResponse.json();
                    if (fallbackData && fallbackData.recommendation) {
                        addMessage(fallbackData.recommendation);
                        hasSelectedRecommendation = true;
                    } else {
                        throw new Error("Invalid fallback format");
                    }

                } catch (fallbackError) {
                    console.error("Fallback generator also failed:", fallbackError);

                    // Final fallback to static recommendations
                    const staticRecs = [
                        "Yo, check this out! AI for Good Hackathon: A virtual hackathon focused on developing AI solutions for social impact challenges. (https://example.com/ai-hackathon)",
                        "Found this for u! Machine Learning Workshop: Hands-on workshop covering the latest ML techniques with expert mentors to guide you. (https://example.com/ml-workshop)",
                        "This is fire! Data Science Meetup: Connect with data professionals and learn about the latest trends in data science and analytics. (https://example.com/data-meetup)"
                    ];

                    // Select a random recommendation
                    const randomRec = staticRecs[Math.floor(Math.random() * staticRecs.length)];
                    addMessage(randomRec);
                    hasSelectedRecommendation = true;
                }
            }

        } catch (error) {
            console.error("Error fetching recommendation:", error);
            addMessage("Sorry, I couldn't find a recommendation right now. Let's chat about what you're looking for instead!");
        } finally {
            // Re-enable the recommend button
            if (recommendButton) {
                recommendButton.disabled = false;
                recommendButton.innerHTML = '<i class="fas fa-lightbulb"></i> Recommend Opportunity';
            }
        }
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

    // Recommend button event listener
    if (recommendButton) {
        recommendButton.addEventListener('click', fetchAndDisplayRecommendation);
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

    // Initialize the chat when the page loads
    const savedProfile = localStorage.getItem('userProfile');

    if (savedProfile) {
        // If we have a saved profile, load it
        appConfig.userProfile = JSON.parse(savedProfile);
        appConfig.userOnboarded = true;
    }
    // Don't start onboarding automatically - the chat should start blank

    // When the page loads, start with the profile tab
    // On profile update, move to recommendations tab
    // Chat tab now has initial recommendations from the API
});