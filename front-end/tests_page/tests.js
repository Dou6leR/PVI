// Tests & AI Self-Check aligned with Personal Chats and Private RAG
let currentQuiz = null;
let userAnswers = {};
let userChats = [];
let previousQuestions = [];
let lastTestSummary = null;
let currentGeneratedNote = null;

document.addEventListener("DOMContentLoaded", () => {
    loadUserChatsForTests();
    loadSavedStudyNotes();

    const chatSelect = document.getElementById("testChatSelect");
    if (chatSelect) {
        chatSelect.addEventListener("change", () => {
            previousQuestions = [];
            updateSelectedChatKnowledge();
        });
    }

    const topicInput = document.getElementById("testTopic");
    if (topicInput) {
        topicInput.addEventListener("input", () => {
            previousQuestions = [];
        });
    }

    const btnGenerate = document.getElementById("btnGenerateQuiz");
    if (btnGenerate) {
        btnGenerate.addEventListener("click", handleGenerateQuiz);
    }

    const btnSubmit = document.getElementById("btnSubmitQuiz");
    if (btnSubmit) {
        btnSubmit.addEventListener("click", handleSubmitQuiz);
    }

    const btnReset = document.getElementById("btnResetQuiz");
    if (btnReset) {
        btnReset.addEventListener("click", handleResetQuiz);
    }

    const btnStudyCoach = document.getElementById("btnStudyCoach");
    if (btnStudyCoach) {
        btnStudyCoach.addEventListener("click", handleGenerateStudyNote);
    }

    const btnDownloadCurrent = document.getElementById("btnDownloadCurrentNote");
    if (btnDownloadCurrent) {
        btnDownloadCurrent.addEventListener("click", () => {
            if (currentGeneratedNote) {
                downloadMarkdownFile(currentGeneratedNote.topic, currentGeneratedNote.content_md);
            }
        });
    }
});

async function loadUserChatsForTests() {
    const select = document.getElementById("testChatSelect");
    const studentId = sessionStorage.getItem("studentId");
    if (!select) return;

    if (!studentId) {
        window.location.href = "../index.html";
        return;
    }

    try {
        const resp = await fetch(`http://localhost:8000/api/v1/message/user_chats/${studentId}`, {
            method: "GET",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            }
        });
        if (resp.ok) {
            const data = await resp.json();
            userChats = data.data || [];
        }
    } catch (e) {
        console.warn("Could not load user chats:", e);
        userChats = [];
    }

    select.innerHTML = "";

    userChats.forEach((chat) => {
        const opt = document.createElement("option");
        opt.value = chat.id;
        opt.setAttribute("data-subject", chat.subject || "");
        const subjText = chat.subject ? ` (${chat.subject})` : "";
        opt.textContent = `${chat.is_ai ? "🤖 " : "💬 "}${chat.chat_name}${subjText}`;
        select.appendChild(opt);
    });

    const freeOpt = document.createElement("option");
    freeOpt.value = "";
    freeOpt.setAttribute("data-subject", "");
    freeOpt.textContent = "Довільна тема (без прив'язки до чату)";
    select.appendChild(freeOpt);

    updateSelectedChatKnowledge();
}

async function updateSelectedChatKnowledge() {
    const select = document.getElementById("testChatSelect");
    const statusEl = document.getElementById("chatKnowledgeStatus");
    const studentId = sessionStorage.getItem("studentId");
    if (!select || !statusEl || !studentId) return;

    const chatId = select.value;
    if (!chatId) {
        statusEl.textContent = "💡 Введіть будь-яку тему вище — AI згенерує тест без прив'язки до файлів.";
        return;
    }

    const selectedOpt = select.options[select.selectedIndex];
    const subject = selectedOpt ? (selectedOpt.getAttribute("data-subject") || "") : "";

    try {
        const url = `http://localhost:8000/api/v1/ai/rag/documents?chat_id=${encodeURIComponent(chatId)}&subject=${encodeURIComponent(subject)}&student_id=${encodeURIComponent(studentId)}`;
        const resp = await fetch(url);
        if (resp.ok) {
            const data = await resp.json();
            const docs = data.documents || [];
            if (docs.length > 0) {
                const names = docs.map((d) => d.filename).join(", ");
                statusEl.innerHTML = `📚 <b>Файли в цьому чаті (${docs.length}):</b> ${escapeHtml(names)} — можна залишити тему порожньою, тест сформується по них.`;
            } else {
                statusEl.textContent = "📚 У цьому чаті ще немає завантажених PDF. Введіть тему тесту вище або завантажте PDF у Messages.";
            }
        }
    } catch (e) {
        statusEl.textContent = "";
    }
}

async function handleGenerateQuiz() {
    const btn = document.getElementById("btnGenerateQuiz");
    const select = document.getElementById("testChatSelect");
    const topicInput = document.getElementById("testTopic");
    const countInput = document.getElementById("testCount");
    const studentId = sessionStorage.getItem("studentId");

    if (!studentId) {
        window.location.href = "../index.html";
        return;
    }

    const chatId = select ? select.value : "";
    const selectedOpt = select && select.selectedIndex >= 0 ? select.options[select.selectedIndex] : null;
    const subject = selectedOpt ? (selectedOpt.getAttribute("data-subject") || "") : "";
    const topic = topicInput ? topicInput.value.trim() : "";
    const numQuestions = countInput ? parseInt(countInput.value, 10) : 3;

    if (isNaN(numQuestions) || numQuestions < 1 || numQuestions > 10) {
        alert("Вкажіть кількість питань від 1 до 10.");
        return;
    }

    if (!chatId && !topic) {
        alert("Оберіть чат із завантаженими PDF або введіть тему тесту.");
        return;
    }

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="loading-spinner"></span> Генерація ${numQuestions} питань...`;

    try {
        const response = await fetch("http://localhost:8000/api/v1/ai/tests/generate-quiz", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                chat_id: chatId || null,
                student_id: Number(studentId),
                subject,
                topic,
                num_questions: numQuestions,
                previous_questions: previousQuestions
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || `HTTP ${response.status}`);
        }

        const newQuestions = (data.questions || []).map(q => q.question).filter(Boolean);
        previousQuestions = [...previousQuestions, ...newQuestions].slice(-30);

        renderQuiz(data);
    } catch (err) {
        console.error("Error generating test:", err);
        alert("Не вдалося згенерувати тест: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function renderQuiz(quizData) {
    currentQuiz = quizData;
    userAnswers = {};

    const container = document.getElementById("questionsList");
    const metaHeader = document.getElementById("quizMetaHeader");
    const metaTitle = document.getElementById("quizMetaTitle");
    const badgeSource = document.getElementById("badgeSource");
    const badgeSubject = document.getElementById("badgeSubject");
    const actionsDiv = document.getElementById("quizActions");
    const scoreBadge = document.getElementById("scoreBadge");
    const btnSubmit = document.getElementById("btnSubmitQuiz");
    const btnReset = document.getElementById("btnResetQuiz");
    const btnStudyCoach = document.getElementById("btnStudyCoach");
    const coachBox = document.getElementById("studyCoachBox");

    if (metaHeader) metaHeader.style.display = "flex";
    if (actionsDiv) actionsDiv.style.display = "flex";
    if (scoreBadge) scoreBadge.style.display = "none";
    if (btnSubmit) btnSubmit.style.display = "inline-block";
    if (btnReset) btnReset.style.display = "none";
    if (btnStudyCoach) btnStudyCoach.style.display = "none";
    if (coachBox) coachBox.style.display = "none";
    lastTestSummary = null;
    currentGeneratedNote = null;

    if (metaTitle) metaTitle.textContent = quizData.topic || "Тест для самоперевірки";
    if (badgeSource) badgeSource.textContent = quizData.source || "AI";
    if (badgeSubject) {
        if (quizData.subject && quizData.subject.trim() !== "") {
            badgeSubject.textContent = quizData.subject;
            badgeSubject.style.display = "inline-block";
        } else {
            badgeSubject.style.display = "none";
        }
    }

    if (!container) return;
    container.innerHTML = "";

    const questions = quizData.questions || [];
    if (questions.length === 0) {
        if (actionsDiv) actionsDiv.style.display = "none";
        container.innerHTML = `<div class="empty-quiz-state">Не вдалося сформувати запитання. Перевірте тему або завантажте PDF у чат.</div>`;
        return;
    }

    questions.forEach((q, qIdx) => {
        const card = document.createElement("div");
        card.className = "question-card";
        card.id = `qCard_${q.id || qIdx}`;

        const qTitle = document.createElement("div");
        qTitle.className = "question-title";
        qTitle.innerHTML = `<span><strong>${qIdx + 1}.</strong></span> <span>${escapeHtml(q.question)}</span>`;
        card.appendChild(qTitle);

        const optionsDiv = document.createElement("div");
        optionsDiv.className = "question-options";

        q.options.forEach((optText, optIdx) => {
            const label = document.createElement("label");
            label.className = "option-label";
            label.id = `optLabel_${q.id || qIdx}_${optIdx}`;

            const radio = document.createElement("input");
            radio.type = "radio";
            radio.name = `question_${q.id || qIdx}`;
            radio.value = optIdx;
            radio.addEventListener("change", () => {
                userAnswers[q.id || qIdx] = optIdx;
            });

            label.appendChild(radio);
            const span = document.createElement("span");
            span.textContent = optText;
            label.appendChild(span);

            optionsDiv.appendChild(label);
        });
        card.appendChild(optionsDiv);

        const expBox = document.createElement("div");
        expBox.className = "explanation-box";
        expBox.id = `exp_${q.id || qIdx}`;
        expBox.innerHTML = `<strong>💡 Пояснення:</strong> ${escapeHtml(q.explanation || "Відповідь відповідає матеріалу.")}`;
        card.appendChild(expBox);

        container.appendChild(card);
    });
}

function handleSubmitQuiz() {
    if (!currentQuiz || !currentQuiz.questions) return;

    const questions = currentQuiz.questions;
    const answeredCount = Object.keys(userAnswers).length;

    if (answeredCount < questions.length) {
        if (!confirm(`Ви відповіли на ${answeredCount} з ${questions.length} запитань. Перевірити зараз?`)) {
            return;
        }
    }

    let correctCount = 0;
    const mistakes = [];

    questions.forEach((q, qIdx) => {
        const qKey = q.id || qIdx;
        const selectedOpt = userAnswers[qKey];
        const card = document.getElementById(`qCard_${qKey}`);
        const expBox = document.getElementById(`exp_${qKey}`);

        if (expBox) expBox.classList.add("visible");

        const radios = document.querySelectorAll(`input[name="question_${qKey}"]`);
        radios.forEach((r) => (r.disabled = true));

        q.options.forEach((_, optIdx) => {
            const label = document.getElementById(`optLabel_${qKey}_${optIdx}`);
            if (!label) return;

            if (optIdx === q.correct_index) {
                label.classList.add("correct");
            } else if (selectedOpt === optIdx && optIdx !== q.correct_index) {
                label.classList.add("incorrect");
            }
        });

        if (card) {
            if (selectedOpt === q.correct_index) {
                card.classList.add("answered-correct");
                card.classList.remove("answered-incorrect");
                correctCount++;
            } else {
                card.classList.add("answered-incorrect");
                card.classList.remove("answered-correct");
                mistakes.push({
                    question: q.question,
                    user_answer: selectedOpt !== undefined ? q.options[selectedOpt] : "Не обрано",
                    correct_answer: q.options[q.correct_index],
                    explanation: q.explanation || ""
                });
            }
        }
    });

    const percent = Math.round((correctCount / questions.length) * 100);
    const scoreBadge = document.getElementById("scoreBadge");
    const btnSubmit = document.getElementById("btnSubmitQuiz");
    const btnReset = document.getElementById("btnResetQuiz");
    const btnStudyCoach = document.getElementById("btnStudyCoach");
    const select = document.getElementById("testChatSelect");

    lastTestSummary = {
        chat_id: select && select.value ? select.value : null,
        subject: currentQuiz.subject || "",
        topic: currentQuiz.topic || "Тест",
        score: correctCount,
        total: questions.length,
        mistakes
    };

    if (scoreBadge) {
        scoreBadge.style.display = "inline-block";
        scoreBadge.innerHTML = `Результат: <strong>${correctCount} / ${questions.length}</strong> (${percent}%) ${percent >= 70 ? "🎉 Чудово!" : "📚 Варто повторити матеріал"}`;
    }

    if (btnSubmit) btnSubmit.style.display = "none";
    if (btnReset) btnReset.style.display = "inline-block";
    if (btnStudyCoach) btnStudyCoach.style.display = "inline-flex";
}

function handleResetQuiz() {
    if (!currentQuiz) return;
    renderQuiz(currentQuiz);
}

async function handleGenerateStudyNote() {
    const btn = document.getElementById("btnStudyCoach");
    const studentId = sessionStorage.getItem("studentId");
    if (!studentId || !lastTestSummary) return;

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<span class="loading-spinner"></span> n8n AI готує шпаргалку...`;

    try {
        const resp = await fetch("http://localhost:8000/api/v1/ai/tests/study-coach", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                student_id: Number(studentId),
                chat_id: lastTestSummary.chat_id,
                subject: lastTestSummary.subject,
                topic: lastTestSummary.topic,
                score: lastTestSummary.score,
                total: lastTestSummary.total,
                mistakes: lastTestSummary.mistakes
            })
        });
        const data = await resp.json();
        if (!resp.ok) {
            throw new Error(data.detail || `HTTP ${resp.status}`);
        }

        currentGeneratedNote = data;
        renderStudyCoachBox(data);
        await loadSavedStudyNotes();
    } catch (err) {
        console.error("Study coach error:", err);
        alert("Не вдалося створити шпаргалку: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

function renderStudyCoachBox(note) {
    const box = document.getElementById("studyCoachBox");
    const modeBadge = document.getElementById("coachModeBadge");
    const srcBadge = document.getElementById("coachSourceBadge");
    const contentEl = document.getElementById("studyCoachContent");

    if (!box || !contentEl) return;
    box.style.display = "block";
    if (modeBadge) {
        modeBadge.textContent = note.coach_mode === "remedial" ? "🔁 План повторення (< 70%)" : "🚀 Поглиблення (>= 70%)";
    }
    if (srcBadge) {
        srcBadge.textContent = note.source || "n8n AI Study Coach";
    }
    contentEl.innerHTML = formatCoachMarkdown(note.content_md);
}

async function loadSavedStudyNotes() {
    const listEl = document.getElementById("savedNotesList");
    const studentId = sessionStorage.getItem("studentId");
    if (!listEl || !studentId) return;

    try {
        const resp = await fetch(`http://localhost:8000/api/v1/ai/tests/study-notes?student_id=${encodeURIComponent(studentId)}`);
        if (!resp.ok) return;
        const data = await resp.json();
        const notes = data.notes || [];

        if (notes.length === 0) {
            listEl.innerHTML = `<div class="empty-notes-state">Поки що немає збережених шпаргалок.</div>`;
            return;
        }

        listEl.innerHTML = "";
        notes.forEach((note) => {
            const card = document.createElement("div");
            card.className = "saved-note-card";

            const dateStr = note.created_at ? new Date(note.created_at).toLocaleString("uk-UA") : "";
            const modeLabel = note.coach_mode === "remedial" ? "Повторення" : "Поглиблення";

            const top = document.createElement("div");
            top.className = "saved-note-top";
            top.innerHTML = `
                <div>
                    <div class="saved-note-title">${escapeHtml(note.topic)}</div>
                    <div class="saved-note-meta">Результат: <b>${note.score}/${note.total} (${note.percent}%)</b> · ${modeLabel} · ${escapeHtml(note.source)} · ${dateStr}</div>
                </div>
            `;

            const actions = document.createElement("div");
            actions.className = "saved-note-actions";

            const toggleBtn = document.createElement("button");
            toggleBtn.className = "btn-note-toggle";
            toggleBtn.textContent = "Відкрити";

            const dlBtn = document.createElement("button");
            dlBtn.className = "btn-download-md";
            dlBtn.textContent = "⬇️ .md";
            dlBtn.onclick = () => downloadMarkdownFile(note.topic, note.content_md);

            const delBtn = document.createElement("button");
            delBtn.className = "btn-note-delete";
            delBtn.textContent = "🗑️";
            delBtn.title = "Видалити шпаргалку";
            delBtn.onclick = () => deleteStudyNote(note.id);

            actions.appendChild(toggleBtn);
            actions.appendChild(dlBtn);
            actions.appendChild(delBtn);
            top.appendChild(actions);

            const body = document.createElement("div");
            body.className = "saved-note-body";
            body.innerHTML = formatCoachMarkdown(note.content_md);

            toggleBtn.onclick = () => {
                const isOpen = body.classList.toggle("open");
                toggleBtn.textContent = isOpen ? "Згорнути" : "Відкрити";
            };

            card.appendChild(top);
            card.appendChild(body);
            listEl.appendChild(card);
        });
    } catch (e) {
        console.warn("Could not load saved study notes:", e);
    }
}

async function deleteStudyNote(noteId) {
    const studentId = sessionStorage.getItem("studentId");
    if (!studentId || !confirm("Видалити цю шпаргалку?")) return;
    try {
        const resp = await fetch(`http://localhost:8000/api/v1/ai/tests/study-notes/${encodeURIComponent(noteId)}?student_id=${encodeURIComponent(studentId)}`, {
            method: "DELETE"
        });
        if (resp.ok) {
            await loadSavedStudyNotes();
        }
    } catch (e) {
        console.error("Failed to delete note:", e);
    }
}

function downloadMarkdownFile(topic, contentMd) {
    const safeName = (topic || "study_note").replace(/[^\wа-яА-ЯіїєґІЇЄҐ\s-]/g, "").trim().replace(/\s+/g, "_") || "study_note";
    const blob = new Blob([contentMd || ""], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeName}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function formatCoachMarkdown(md) {
    const safe = escapeHtml(md || "");
    return safe
        .replace(/^### (.*)$/gm, '<h4 style="margin:10px 0 4px; color:#1e293b;">$1</h4>')
        .replace(/^## (.*)$/gm, '<h3 style="margin:12px 0 6px; color:#0f172a;">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, "<b>$1</b>")
        .replace(/\*(.*?)\*/g, "<i>$1</i>")
        .replace(/`([^`]+)`/g, '<code style="background:#e2e8f0;padding:2px 5px;border-radius:4px;">$1</code>');
}

function escapeHtml(text) {
    if (!text) return "";
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
