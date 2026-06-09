document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");

  // Chat elements
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatMessages = document.getElementById("chat-messages");
  const chatSubmit = document.getElementById("chat-submit");

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      
      // Clear and repopulate activity select (keep the placeholder option)
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details], index) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft = details.max_participants - details.participants.length;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
        `;

        const participantsToggle = document.createElement("button");
        participantsToggle.type = "button";
        participantsToggle.className = "participants-toggle";
        participantsToggle.textContent = "View Participants";

        const participantsContainer = document.createElement("div");
        const participantsId = `participants-${index}-${name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
        participantsContainer.id = participantsId;
        participantsContainer.className = "participants-container hidden";

        participantsToggle.setAttribute("aria-expanded", "false");
        participantsToggle.setAttribute("aria-controls", participantsId);

        if (details.participants.length > 0) {
          const participantsList = document.createElement("ul");
          participantsList.className = "participants-list";

          details.participants.forEach((participant) => {
            const participantItem = document.createElement("li");
            participantItem.textContent = participant;
            participantsList.appendChild(participantItem);
          });

          participantsContainer.appendChild(participantsList);
        } else {
          const emptyState = document.createElement("p");
          emptyState.className = "participants-empty";
          emptyState.textContent = "No participants registered yet.";
          participantsContainer.appendChild(emptyState);
        }

        participantsToggle.addEventListener("click", () => {
          const isHidden = participantsContainer.classList.contains("hidden");
          participantsContainer.classList.toggle("hidden");
          participantsToggle.setAttribute("aria-expanded", String(isHidden));
          participantsToggle.textContent = isHidden ? "Hide Participants" : "View Participants";
        });

        activityCard.appendChild(participantsToggle);
        activityCard.appendChild(participantsContainer);

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Handle chat form submission with SSE streaming
  chatForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const prompt = chatInput.value.trim();
    if (!prompt) return;

    // Disable input while processing
    chatInput.disabled = true;
    chatSubmit.disabled = true;

    // Add user message to chat
    const userMessage = document.createElement("div");
    userMessage.className = "chat-message user-message";
    userMessage.textContent = prompt;
    chatMessages.appendChild(userMessage);

    // Clear input
    chatInput.value = "";

    // Create assistant message placeholder
    const assistantMessage = document.createElement("div");
    assistantMessage.className = "chat-message assistant-message";
    chatMessages.appendChild(assistantMessage);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const response = await fetch("/assistant/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value, { stream: true });
        const lines = text.split("\n");

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6);
            if (data === "[DONE]") {
              // Stream complete - refresh activities in case a signup occurred
              await fetchActivities();
            } else {
              // Append chunk to assistant message
              assistantMessage.textContent += data;
              // Auto-scroll
              chatMessages.scrollTop = chatMessages.scrollHeight;
            }
          }
        }
      }
    } catch (error) {
      assistantMessage.textContent = "Sorry, something went wrong. Please try again.";
      assistantMessage.classList.add("error-message");
      console.error("Error with assistant:", error);
    } finally {
      // Re-enable input
      chatInput.disabled = false;
      chatSubmit.disabled = false;
      chatInput.focus();
    }
  });

  // Initialize app
  fetchActivities();
});
