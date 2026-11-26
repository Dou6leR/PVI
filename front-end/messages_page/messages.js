let chats = [];
let current_chat = null;
let users = [];
let chats_body = document.getElementsByClassName("chats")[0];
const send_button = document.getElementById("send-message");
let message_wrapper = document.getElementsByClassName("messages")[0];
let modal_add_member = document.getElementById("modal_member");
let btn_member = document.getElementById("btn_add_member");
let btn_chat = document.getElementById("button-room");
let input_area = document.getElementsByClassName("input-area")[0];
let close_add_member = document.getElementsByClassName("close")[0];
let input_search_block = document.getElementById("input-search-block");
let members = document.getElementsByClassName("members-avatars")[0];

const btn_upload_pdf = document.getElementById("btn-upload-pdf");
const pdf_file_input = document.getElementById("pdf-file-input");

const inputHandler = function(e) {
    searchStudents(e.target.value);
};

if (input_search_block) {
    input_search_block.addEventListener('input', inputHandler);
}

// PDF Upload Handler
if (btn_upload_pdf && pdf_file_input) {
    btn_upload_pdf.onclick = function() {
        const activeChat = getActiveChat();
        if (!activeChat) {
            alert("Спочатку створіть або оберіть чат для завантаження файлу в його базу знань.");
            return;
        }
        pdf_file_input.click();
    };

    pdf_file_input.onchange = async function(e) {
        const file = e.target.files[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith(".pdf")) {
            alert("Будь ласка, оберіть файл формату PDF.");
            return;
        }

        const currentStudentId = sessionStorage.getItem("studentId");
        if (!currentStudentId) {
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";
            return;
        }

        const activeChat = getActiveChat();
        if (!activeChat) {
            alert("Спочатку створіть або оберіть чат.");
            return;
        }
        const subject = activeChat.subject || "";
        const scopeLabel = subject ? ` ("<b>${subject}</b>")` : "";

        const tempNotify = document.createElement("div");
        tempNotify.classList.add("system-notification");
        tempNotify.innerHTML = `⏳ Завантаження та індексація документа "<b>${file.name}</b>" у вашу приватну базу знань${scopeLabel}...`;
        message_wrapper.appendChild(tempNotify);
        message_wrapper.scrollTop = message_wrapper.scrollHeight;

        const formData = new FormData();
        formData.append("file", file);
        formData.append("subject", subject);
        formData.append("chat_id", current_chat);
        formData.append("student_id", currentStudentId);

        try {
            const response = await fetch("http://localhost:8000/api/v1/ai/rag/upload-pdf", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Помилка завантаження");
            }

            const result = await response.json();
            tempNotify.innerHTML = `✅ <b>${result.filename}</b> успішно проіндексовано у вашій приватній базі знань! Оброблено ${result.pages_extracted} стор. (${result.chunks_indexed} фрагментів).`;
            loadChatDocsBadge(current_chat, subject);
        } catch (err) {
            console.error("PDF upload error:", err);
            tempNotify.style.backgroundColor = "#fee2e2";
            tempNotify.style.borderColor = "#fca5a5";
            tempNotify.style.color = "#991b1b";
            tempNotify.innerHTML = `❌ Помилка завантаження PDF: ${err.message}`;
        } finally {
            pdf_file_input.value = "";
        }
    };
}

function getActiveChat() {
    return chats.find(c => c.id == current_chat) || null;
}

// Send Message Handler
send_button.onclick = async function(event) {
    if (window.location.pathname.includes("messages_page")) {
        let input = document.getElementById("input-area-block");
        let studentId = sessionStorage.getItem("studentId");
        if (!studentId) {
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";
            return;
        }
        if (!input.value.trim()) return;

        const text = input.value.trim();
        input.value = '';

        const activeChat = getActiveChat();

        // 1. Handling AI Chat
        if (activeChat && activeChat.is_ai) {
            const userMsg = {
                message_type: "message",
                message: text,
                room_id: current_chat,
                user: Number(studentId)
            };
            activeChat.messages.push(userMsg);
            insertMessage(userMsg);

            // Typing indicator
            const typingMsg = document.createElement("div");
            typingMsg.id = "ai-typing-indicator";
            typingMsg.classList.add("message", "ai");
            typingMsg.innerHTML = `<i>🤖 CMS AI Assistant аналізує запит та інструменти...</i>`;
            message_wrapper.appendChild(typingMsg);
            message_wrapper.scrollTop = message_wrapper.scrollHeight;

            try {
                const response = await fetch("http://localhost:8000/api/v1/ai/chat", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": "Basic " + sessionStorage.getItem("credentials")
                    },
                    body: JSON.stringify({
                        message: text,
                        subject: activeChat.subject || "",
                        chat_id: current_chat,
                        student_id: Number(studentId)
                    })
                });

                const indicator = document.getElementById("ai-typing-indicator");
                if (indicator) indicator.remove();

                if (!response.ok) {
                    throw new Error("Помилка генерації відповіді");
                }

                const data = await response.json();
                
                let badgeParts = [];
                if (data.provider) {
                    badgeParts.push(`🧠 ${data.provider}`);
                }
                if (data.tools_called && data.tools_called.length > 0) {
                    const toolNames = data.tools_called.map(t => t.tool.replace("tool_", "")).join(", ");
                    badgeParts.push(`🔧 Інструменти: ${toolNames}`);
                }
                let toolBadgeHtml = badgeParts.length > 0
                    ? `<div class="tool-badge">${badgeParts.join(" · ")}</div>`
                    : "";

                const aiReply = {
                    message_type: "message",
                    message: data.response,
                    room_id: current_chat,
                    user: 9999,
                    toolBadgeHtml: toolBadgeHtml
                };
                activeChat.messages.push(aiReply);
                insertMessage(aiReply);

            } catch (err) {
                console.error("AI Error:", err);
                const indicator = document.getElementById("ai-typing-indicator");
                if (indicator) indicator.remove();
                insertMessage({
                    message: "Вибачте, виникла помилка під час зв'язку з CMS AI Assistant.",
                    user: 9999,
                    room_id: current_chat
                });
            }
            return;
        }

        // 2. Standard WebSocket Peer-to-Peer Chat
        const message = {
            message_type: "message",
            message: text,
            room_id: current_chat,
            user: studentId
        };
        if (typeof ws !== "undefined" && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
        insertMessage(message);
    }
};

btn_chat.onclick = function(event) {
    users = [];
    members.innerHTML = ``;
    const prev = document.getElementById(current_chat);
    if (prev) prev.classList.remove("active");
    current_chat = "button-room";
    message_wrapper.innerHTML = ``;
    document.getElementById("button-room").classList.add("active");
    showAddChat();
};

document.getElementById("input-area-block").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        send_button.click();
    }
});

document.addEventListener("DOMContentLoaded", fetchChats);
document.addEventListener("DOMContentLoaded", () => { sessionStorage.removeItem("myItem"); });

async function fetchChats() {
    const studentId = sessionStorage.getItem("studentId");
    if (!studentId) {
        window.location.href = "../index.html";
        return;
    }

    try {
        let dbChats = [];
        try {
            const response = await fetch(`http://localhost:8000/api/v1/message/user_chats/${studentId}`, {
                method: "GET",
                headers: {
                    "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                    "Content-Type": "application/json"
                }
            });
            if (response.ok) {
                const data = await response.json();
                dbChats = data.data || [];
            }
        } catch (e) {
            console.log("Error fetching user chats:", e);
        }

        // Strict per-user chats from DB (no preloaded shared preset chats)
        chats = dbChats;
        renderChatList();

        if (chats.length > 0) {
            current_chat = chats[0].id;
            const firstEl = document.getElementById(current_chat);
            if (firstEl) firstEl.classList.add("active");
            renderActiveChat(chats[0]);
            input_area.style.display = "flex";
        } else {
            current_chat = null;
            document.getElementsByClassName("chat-header")[0].innerHTML = "Створіть свій перший персональний чат";
            showAddChat();
        }
    } catch (error) {
        console.error("Error in fetchChats:", error);
    }
}

function renderChatList() {
    // Keep button-room
    chats_body.innerHTML = '';
    chats_body.appendChild(btn_chat);

    chats.forEach(element => {
        let new_chat = document.createElement("div");
        new_chat.classList.add("chat-room");
        new_chat.id = element.id;

        const hasSubject = element.subject && element.subject.trim() !== "";
        const subjectBadge = hasSubject ? ` <span class="subject-badge ${element.is_ai ? 'ai-badge' : ''}">${element.subject}</span>` : "";
        new_chat.innerHTML = `${element.is_ai ? '🤖 ' : '💬 '} ${element.chat_name}${subjectBadge}`;
        new_chat.onclick = selectChat;
        chats_body.appendChild(new_chat);
    });
}

async function loadChatDocsBadge(chatId, subject) {
    const badgeEl = document.getElementById("rag-docs-badge");
    const studentId = sessionStorage.getItem("studentId");
    if (!badgeEl || !studentId || !chatId) return;

    try {
        const url = `http://localhost:8000/api/v1/ai/rag/documents?chat_id=${encodeURIComponent(chatId)}&subject=${encodeURIComponent(subject || '')}&student_id=${encodeURIComponent(studentId)}`;
        const resp = await fetch(url);
        if (resp.ok) {
            const data = await resp.json();
            const count = (data.documents || []).length;
            if (count > 0) {
                const names = data.documents.map(d => d.filename).join(", ");
                badgeEl.textContent = `📚 PDF (${count}): ${names}`;
                badgeEl.style.display = "inline-block";
            } else {
                badgeEl.textContent = "📚 База знань порожня (завантажте PDF)";
                badgeEl.style.display = "inline-block";
            }
        }
    } catch (e) {
        console.debug("Failed to load docs count", e);
    }
}

function renderActiveChat(chat) {
    const subject = (chat.subject || "").trim();
    const subjectHtml = subject ? ` <span class="subject-badge">${subject}</span>` : "";
    document.getElementsByClassName("chat-header")[0].innerHTML = `${chat.is_ai ? '🤖 ' : ''}${chat.chat_name}${subjectHtml} <span id="rag-docs-badge" class="subject-badge" style="display:none; background:#eef2ff; color:#4338ca; margin-left:6px;"></span>`;
    message_wrapper.innerHTML = "";
    members.innerHTML = "";

    if (chat.is_ai) {
        btn_member.style.display = "none";
        const botAvatar = document.createElement("span");
        botAvatar.setAttribute("data-tooltip", "CMS AI Assistant");
        botAvatar.style.backgroundColor = "#4f46e5";
        botAvatar.innerHTML = "🤖";
        botAvatar.style.display = "flex";
        botAvatar.style.alignItems = "center";
        botAvatar.style.justifyContent = "center";
        members.appendChild(botAvatar);
        loadChatDocsBadge(chat.id, subject);
    } else {
        btn_member.style.display = "inline-block";
        insertUsers(chat.users || []);
    }

    if (chat.messages && chat.messages.length > 0) {
        chat.messages.forEach(element => { insertMessage(element); });
    } else if (chat.is_ai) {
        const topicNote = subject ? ` (${subject})` : "";
        insertMessage({
            user: 9999,
            room_id: chat.id,
            message: `👋 Вітаю у вашому персональному чаті **'${chat.chat_name}'**${topicNote}!\n\nНатисніть **📎 PDF**, щоб завантажити власні файли до приватної бази знань цього чату, або поставте запитання.`
        });
    }
}

async function fetchChat(chat_id) {
    try {
        const response = await fetch(`http://localhost:8000/api/v1/message/chat/` + chat_id, {
            method: "GET",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            }
        });
        if (!response.ok) throw new Error(response.status);
        const data = await response.json();

        let idx = chats.findIndex(c => c.id == data.id);
        if (idx !== -1) {
            chats[idx] = data;
        } else {
            chats.push(data);
            renderChatList();
        }

        if (chat_id == current_chat) {
            renderActiveChat(data);
        }
    } catch (error) {
        console.error("Error fetching chat:", error);
    }
}

function insertMessage(element) {
    if ("room_id" in element) {
        if (element.room_id != current_chat) return;
    }

    const currentStudentId = sessionStorage.getItem("studentId");
    let new_message = document.createElement("div");
    new_message.classList.add("message");

    // AI message styling
    if (element.user === 9999 || element.user === 9991 || element.user === 9992 || element.user === 9993 || element.user === "ai") {
        new_message.classList.add("ai");
        let badgeHtml = element.toolBadgeHtml || "";
        new_message.innerHTML = `${badgeHtml}<div><b>🤖 CMS AI Assistant:</b><br>${formatMarkdown(element.message)}</div>`;
        message_wrapper.appendChild(new_message);
        message_wrapper.scrollTop = message_wrapper.scrollHeight;
        return;
    }

    // System notification
    if (element.user === 9990) {
        new_message.classList.add("system-notification");
        new_message.innerHTML = element.message;
        message_wrapper.appendChild(new_message);
        message_wrapper.scrollTop = message_wrapper.scrollHeight;
        return;
    }

    // Human message
    let activeChat = getActiveChat();
    let authorName = "Student";
    if (activeChat && activeChat.users) {
        let u = activeChat.users.find(usr => usr.id == Number(element.user));
        if (u) authorName = `${u.last_name} ${u.first_name[0]}.`;
    }

    if (element.user == currentStudentId) {
        new_message.classList.add("me");
        authorName = "Я";
    }

    new_message.innerHTML = `<b>${authorName}:</b> ${element.message}`;
    message_wrapper.appendChild(new_message);
    message_wrapper.scrollTop = message_wrapper.scrollHeight;
}

function formatMarkdown(text) {
    if (!text) return "";
    return text
        .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
        .replace(/\*(.*?)\*/g, '<i>$1</i>')
        .replace(/`([^`]+)`/g, '<code style="background:#e5e7eb;padding:2px 4px;border-radius:3px;">$1</code>')
        .replace(/\n/g, '<br>');
}

function selectChat(e) {
    input_area.style.display = "flex";
    let target = e.currentTarget;
    let id = target.id;
    if (id == current_chat) return;

    const prevBtn = document.getElementById("button-room");
    if (prevBtn) prevBtn.classList.remove("active");

    const prevActive = document.getElementById(current_chat);
    if (prevActive) prevActive.classList.remove("active");

    target.classList.add("active");
    current_chat = id;
    fetchChat(current_chat);
}

function showAddChat() {
    input_area.style.display = "none";
    message_wrapper.innerHTML = `
        <div style="max-width: 480px; margin: 20px auto; padding: 20px; background: #fff; border: 1px solid #e5e7eb; border-radius: 10px;">
            <h3 style="margin-top:0;">Створити новий чат</h3>
            <p style="font-size:13px; color:#64748b; margin-bottom:14px;">Введіть будь-яку назву чату. Кожен чат і завантажені до нього PDF-файли належать лише вашому обліковому запису.</p>
            <div class="create-chat-field">
                <label>Назва чату:</label>
                <input id="input-chat-name" type="text" placeholder="Введіть будь-яку назву чату" autocomplete="off" />
            </div>
            <div class="create-chat-field">
                <label>Дисципліна / тема (необов'язково):</label>
                <input id="input-chat-subject" type="text" placeholder="Необов'язково (можна залишити порожнім)" autocomplete="off" />
            </div>
            <div class="create-chat-ai-toggle">
                <input type="checkbox" id="check-is-ai" checked />
                <label for="check-is-ai"><b>Підключити CMS AI Assistant (персональний помічник + приватний RAG)</b></label>
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 15px;">
                <button id="btn-cancel-chat" class="button_cancel" style="font-size:14px;padding:8px 16px;cursor:pointer;">Скасувати</button>
                <button id="btn-submit-chat" class="button_create" style="font-size:14px;padding:8px 16px;background:#4f46e5;color:white;border:none;border-radius:6px;cursor:pointer;">Створити чат</button>
            </div>
        </div>
    `;

    const cancelBtn = document.getElementById("btn-cancel-chat");
    if (chats.length === 0) {
        cancelBtn.style.display = "none";
    } else {
        cancelBtn.onclick = function() {
            current_chat = chats[0].id;
            const el = document.getElementById(current_chat);
            if (el) el.classList.add("active");
            renderActiveChat(chats[0]);
            input_area.style.display = "flex";
        };
    }

    document.getElementById("btn-submit-chat").onclick = async function() {
        const nameInput = document.getElementById("input-chat-name");
        const subjectInput = document.getElementById("input-chat-subject");
        const isAiCheck = document.getElementById("check-is-ai");
        const studentId = sessionStorage.getItem("studentId");

        if (!studentId) {
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";
            return;
        }

        if (!nameInput.value.trim()) {
            alert("Введіть назву чату!");
            return;
        }

        const subjectValue = subjectInput.value.trim();

        try {
            const response = await fetch("http://localhost:8000/api/v1/message/chat", {
                method: "POST",
                headers: {
                    "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    users: [Number(studentId)],
                    chat_name: nameInput.value.trim(),
                    subject: subjectValue,
                    is_ai: isAiCheck.checked
                })
            });

            if (!response.ok) {
                throw new Error("Не вдалося зберегти чат у базі даних");
            }

            const createdChat = await response.json();
            chats.push(createdChat);
            renderChatList();

            const btnRoom = document.getElementById("button-room");
            if (btnRoom) btnRoom.classList.remove("active");

            current_chat = createdChat.id;
            const chatEl = document.getElementById(createdChat.id);
            if (chatEl) chatEl.classList.add("active");
            renderActiveChat(createdChat);
            input_area.style.display = "flex";
        } catch (err) {
            console.error("Create chat error:", err);
            alert("Помилка створення чату: " + err.message);
        }
    };
}

function insertUsers(usersList) {
    members.innerHTML = '';
    usersList.forEach(u => {
        let avatar = document.createElement("span");
        avatar.setAttribute("data-tooltip", `${u.last_name || ''} ${u.first_name || ''}`);
        avatar.innerHTML = (u.first_name ? u.first_name[0] : "") + (u.last_name ? u.last_name[0] : "");
        avatar.style.display = "inline-flex";
        avatar.style.alignItems = "center";
        avatar.style.justifyContent = "center";
        avatar.style.fontWeight = "bold";
        members.appendChild(avatar);
    });
}

btn_member.onclick = function(event) {
    modal_add_member.style.display = "block";
};
close_add_member.onclick = function(event) {
    event.preventDefault();
    modal_add_member.style.display = "none";
};
window.onclick = function(event) {
    if (event.target == modal_add_member) {
        event.preventDefault();
        modal_add_member.style.display = "none";
    }
};

async function searchStudents(input_search) {
    if (input_search == "") {
        let student_warapper = document.getElementsByClassName("students_from_search")[0];
        student_warapper.innerHTML = ``;
        return;
    }
    try {
        const response = await fetch(`http://localhost:8000/api/v1/student/search?input_search=${input_search}`, {
            method: "GET",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            }
        });
        if (!response.ok) throw new Error(response.status);
        const data = await response.json();
        let studentsList = data.data;
        let student_warapper = document.getElementsByClassName("students_from_search")[0];
        student_warapper.innerHTML = ``;
        studentsList.forEach((student) => {
            let new_student = document.createElement("div");
            new_student.classList.add("student_from_search");
            new_student.id = student.id;
            new_student.innerHTML = `${student.last_name} ${student.first_name} (${student.group})`;
            new_student.onclick = selectStudent;
            student_warapper.appendChild(new_student);
        });
    } catch (error) {
        if (error.message == 401) {
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";
        }
    }
}

function selectStudent(e) {
    let id = e.target.id;
    e.preventDefault();
    modal_add_member.style.display = "none";
    if (users.includes(id)) {
        alert("User is already in chat");
        return;
    }
    let fields = e.target.innerHTML.split(" ");
    let user = {
        last_name: fields[0],
        first_name: fields[1],
        id: id
    };
    insertUsers([user]);
}
