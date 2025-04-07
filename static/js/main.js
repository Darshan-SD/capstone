document.addEventListener("DOMContentLoaded", function () {
    const firstTimeUI = document.getElementById("firstTimeUI");
    const chatContainer = document.getElementById("chatContainer");
    const conversation = document.getElementById("conversation");
    const sendButton = document.getElementById("sendBtn");
    const darkModeToggle = document.getElementById("darkModeToggle");
    const userInputField = document.getElementById("userInput");
    const submitBtn = document.getElementById("submitBtn");
    let chatInput;

    function switchToChatMode(userMessage) {
        if (!userMessage) return;
        
        firstTimeUI.classList.add("hidden");
        chatContainer.classList.remove("hidden");

        chatInput = document.getElementById("chatInput");

        localStorage.setItem('last_user_response', userMessage);
        addMessage(userMessage, "user");

        sendButton.addEventListener("click", submitInput);
        chatInput.addEventListener("keypress", function (event) {
            if (event.key === "Enter") {
                event.preventDefault();
                submitInput();
            }
        });

        processMessage(userMessage);
    }

    function addMessage(text, sender, isHtml = false, isRetry = false) {
        if (!text) return;
        console.log("1st Is Retry: ", isRetry);
        // Hide typing indicator while adding new message
        const typingIndicator = document.getElementById("typingIndicator");
        if (typingIndicator) {
            typingIndicator.style.display = "none";
            conversation.removeChild(typingIndicator);
        }

        // const messageElement = document.createElement("div");
        // messageElement.classList.add("message", sender);

        // Create the container div
        const container = document.createElement("div");
        container.classList.add(`message-container-${sender}`);

        const messageElement = document.createElement("div");
        messageElement.classList.add("message", sender);
        container.appendChild(messageElement);

        if (isRetry) {
            const button = document.createElement("button");
            button.innerHTML = "<i class='fa-solid fa-rotate-right'></i>";
            button.classList.add("retry-button");
            container.appendChild(button);
            button.addEventListener("click", () => {
                // this.classList.toggle("rotate-retry-button");
                removeLastBotUserMessage();
                localStorage.getItem('last_user_response') ? submitInput(localStorage.getItem('last_user_response')) : addMessage("Please refresh the page.", "bot");
            });
        }

        if (isHtml) {
            messageElement.classList.add("prose");
            messageElement.innerHTML = text;
        } else {
            messageElement.innerText = text;
        }

        conversation.appendChild(container);

        // Re-add typing indicator at the very end (hidden by default)
        if (typingIndicator) {
            conversation.appendChild(typingIndicator);
        }

        conversation.scrollTop = conversation.scrollHeight;
    }


    function showTypingIndicator(show) {
        let typingIndicator = document.getElementById("typingIndicator");
        if (!typingIndicator) {
            typingIndicator = document.createElement("p");
            typingIndicator.id = "typingIndicator";
            typingIndicator.className = "typing-indicator text-black italic";
            typingIndicator.innerHTML = "<div id='loader-container' class='flex items-center' ><div class='loader'></div>&nbsp&nbsp&nbsp&nbsp&nbsp<div class='loader-text'></div></div>";
            conversation.appendChild(typingIndicator);
        }
        typingIndicator.style.display = show ? "block" : "none";
    }

    async function processMessage(userMessage) {
        showTypingIndicator(true);

        const requestData = { input: userMessage, isPreset: true };

        const response = await fetch("/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData),
        });

        const data = await response.json();
        showTypingIndicator(false);

        if (data.question) {
            addMessage(data.question, "bot");
        } else if (data.final_response == true) {  // ✅ NEW CHECK FOR FINAL RESPONSE
            addMessage(`<strong>User Level:</strong> ${data.user_level}`, "bot", true);
            addMessage(`<strong>Summary:</strong> ${data.summary}`, "bot", true);

            // ✅ Display Key Elements
            if (data.key_elements && Array.isArray(data.key_elements)) {
                const keyElementsHtml = `<strong>Key Elements:</strong> <ul class="list-disc pl-5">${data.key_elements.map(e => `<li>${e}</li>`).join("")}</ul>`;
                addMessage(keyElementsHtml, "bot", true);
            }

            // ✅ Display Score Breakdown
            if (data.score_breakdown && Array.isArray(data.score_breakdown)) {
                let scoreBreakdownHtml = `<strong>Score Breakdown:</strong> <div class="bg-gray-100 p-3 rounded-md border-l-4 border-gray-500">`;
                data.score_breakdown.forEach((entry, index) => {
                    scoreBreakdownHtml += `
      <div class="mb-2 p-2 bg-gray-50 border border-gray-300 rounded">
        <p><strong>Response ${index + 1}:</strong> ${entry.response}</p>
        <p><strong>Score:</strong> ${entry.score}</p>
        <p><strong>Reasoning:</strong> ${entry.reasoning}</p>
      </div>
    `;
                });
                scoreBreakdownHtml += `</div>`;
                addMessage(scoreBreakdownHtml, "bot", true);
            }

            // ✅ Display RAG Response
            if (data.rag_response) {
                let formattedResponse = `<div class="response-container">`;
                if (data.rag_response.course_title) {
                    formattedResponse += `<h4>${data.rag_response.course_title}</h4>`;
                }
                if (data.rag_response.introduction) {
                    formattedResponse += `<p><strong>Introduction:</strong> ${data.rag_response.introduction}</p>`;
                }
                if (data.rag_response.weeks && Array.isArray(data.rag_response.weeks)) {
                    formattedResponse += `<h3 class="section-title">Course Outline:</h3>`;
                    data.rag_response.weeks.forEach((week, index) => {
                        formattedResponse += `
                  <div class="week-container">
                    <h3>Week ${week.week}: ${week.title}</h3>
                    <p><strong>Description:</strong> ${week.description}</p>
                    <p><strong>Key Takeaways:</strong> ${week.key_takeaways?.join(", ") || "N/A"}</p>
                    <p><strong>Suggested Exercises:</strong> ${week.suggested_exercises || "N/A"}</p>
                    <p><a href="${week.url}" target="_blank" class="resource-link">More Info</a></p>
                  </div>
                `;
                    });
                }
                formattedResponse += `</div>`;
                addMessage(formattedResponse, "bot", true);
            }

            // ✅ Display Sources Links
            if (data.sources_links && data.sources_title) {
                let sourcesLinksHtml = `<strong>Sources:</strong> <ul class="list-disc pl-5">${data.sources_links.map((e, i) => `<li><a href="${e}" target="_blank">${data.sources_title[i]}</a></li>`).join("")}</ul>`;
                addMessage(sourcesLinksHtml, "bot", true);
            }
        } else if (data.greeting == true) { // greeting
            addMessage(`${data.result}`, "bot");
        }
        else if (data.result) {  // ✅ Agent A's Response
            addMessage(`✅ ${data.result}`, "bot");
        }
        console.log(data);
        if (data.retry_error) {
            addMessage(data.retry_error, "bot", false, true);

        }

        if(data.error) {
            addMessage(data.error, "bot");
        }

        if (data.answer_options) {
            let answer_options = data.answer_options;
            const suggestedOptions = document.getElementById("suggestedOptions");
            suggestedOptions.innerHTML = ""; // Clear old

            answer_options.forEach((optionText) => {
                const optionBtn = document.createElement("button");
                optionBtn.className = "p-3 text-black rounded-lg ml-1 mr-1";
                optionBtn.textContent = optionText;
                optionBtn.addEventListener("click", () => submitInput(optionText));
                suggestedOptions.appendChild(optionBtn);
            });

        }
    }

    function submitInput(inputValue = null) {
        const userInput = inputValue || chatInput.value.trim();
        if (!userInput) return;

        localStorage.setItem('last_user_response', userInput);

        addMessage(userInput, "user");
        chatInput.value = "";
        document.getElementById("suggestedOptions").innerHTML = ""; // Clear options
        processMessage(userInput);
    }

    function removeLastBotUserMessage() {
        const botMessages = document.querySelectorAll('.message-container-bot');
        const userMessages = document.querySelectorAll('.message-container-user');
        if (botMessages.length > 0) {
          botMessages[botMessages.length - 1].remove();
        }
        if (userMessages.length > 0) {
          userMessages[userMessages.length - 1].remove();
        }
      }
      

    submitBtn.addEventListener("click", function () {
        const userMessage = userInputField.value.trim();
        if (!userMessage) return;
        switchToChatMode(userMessage);
    });

    userInputField.addEventListener("keypress", function (event) {
        if (event.key === "Enter") {
            event.preventDefault();
            const userMessage = userInputField.value.trim();
            if (!userMessage) return;
            switchToChatMode(userMessage);
        }
    });

    document.querySelectorAll("#suggestionContainer > button").forEach((button) => {
        button.addEventListener("click", function () {
            const selectedTopic = this.innerText;
            switchToChatMode(selectedTopic);
        });
    });
});

// Typewriter Effect
var TxtType = function (el, toRotate, period) {
    this.toRotate = toRotate;
    this.el = el;
    this.loopNum = 0;
    this.period = parseInt(period, 10) || 2000;
    this.txt = '';
    this.tick();
    this.isDeleting = false;
};

TxtType.prototype.tick = function () {
    var i = this.loopNum % this.toRotate.length;
    var fullTxt = this.toRotate[i];

    if (this.isDeleting) {
        this.txt = fullTxt.substring(0, this.txt.length - 1);
    } else {
        this.txt = fullTxt.substring(0, this.txt.length + 1);
    }

    this.el.innerHTML = '<span class="wrap">' + this.txt + '</span>';

    var that = this;
    var delta = 200 - Math.random() * 100;

    if (this.isDeleting) { delta /= 2; }

    if (!this.isDeleting && this.txt === fullTxt) {
        delta = this.period;
        this.isDeleting = true;
    } else if (this.isDeleting && this.txt === '') {
        this.isDeleting = false;
        this.loopNum++;
        delta = 500;
    }

    setTimeout(function () {
        that.tick();
    }, delta);
};

window.onload = function () {
    var elements = document.getElementsByClassName('typewrite');
    for (var i = 0; i < elements.length; i++) {
        var toRotate = elements[i].getAttribute('data-type');
        var period = elements[i].getAttribute('data-period');
        if (toRotate) {
            new TxtType(elements[i], JSON.parse(toRotate), period);
        }
    }
    // INJECT CSS
    var css = document.createElement("style");
    css.type = "text/css";
    css.innerHTML = ".typewrite > .wrap { border-right: 0.08em solid #fff}";
    document.body.appendChild(css);
};