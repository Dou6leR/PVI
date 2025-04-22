var ws;
function toggleBellAnimation() {
    const bell = document.querySelector('.bell_badge');
    const badge = document.querySelector('.badge');
    
    bell.classList.add('swing');
    bell.addEventListener('animationend', function handler() {
        bell.classList.remove('swing');
        badge.style.display = 'inline-block';
        bell.removeEventListener('animationend', handler);

    });
}

document.querySelector('.burger-menu').addEventListener('click', function() {
    const sidebar = document.querySelector('.sidebar');
    
    sidebar.classList.toggle('open');
    
    const bars = document.querySelectorAll('.bar');
    if (sidebar.classList.contains('open')) {
        bars[0].style.transform = 'rotate(-45deg) translate(-5px, 5px)';
        bars[1].style.opacity = '0';
        bars[2].style.transform = 'rotate(45deg) translate(-5px, -5px)';
    } else {
        bars[0].style.transform = 'rotate(0) translate(0, 0)';
        bars[1].style.opacity = '1';
        bars[2].style.transform = 'rotate(0) translate(0, 0)';
    }
});

async function fetchUser(user) {
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/" + user,{
            method: "GET",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            }
        });
        if (!response.ok) {
            throw new Error(response.status);   
        }
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error("Error fetching user:", error);
        if(error.message==401){
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";    
        }    
    }
}
async function fetchUsername(){
    data = await fetchUser(sessionStorage.getItem("studentId"))
    username = document.querySelector(".username");
    username.innerHTML=data.first_name + " " + data.last_name;
}
document.addEventListener("DOMContentLoaded", fetchUsername);
document.addEventListener("DOMContentLoaded", showNotifications);

function initializeWebSocket(studentId, clientId) {
    const wsUrl = `ws://localhost:8000/api/v1/message/${studentId}/ws/${clientId}`;
    ws = new WebSocket(wsUrl);
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    const baseReconnectDelay = 1000;
    
    ws.onmessage = async function (event) {
        console.log(event.data);
        const obj = JSON.parse(JSON.parse(event.data));
        if(obj.message_type == "message"){
            if(document.URL.includes("messages")){
                insertMessage(obj);
            }
            else{
                let user = await fetchUser(obj.user);
                const user_message = {
                    first_name: user.first_name,
                    last_name: user.last_name,
                    message: obj.message
                }
                setNotifications(user_message)
            }
        }
        else if (obj.message_type == "member"){
            let user = await fetchUser(obj.member_id);
            let chat = chats.find(element => {return element.id == obj.room_id});
            console.warn(chat)
            if(chat){
                chat.users.push(user);
                insertUser(user);
            }
            else {
                selectChatFromMessages(obj.room_id);
            }  
        }
        else if (obj.message_type == "chat"){
            selectChatFromMessages(obj.chat_id)
        }
    };

    ws.onerror = function (error) {
        console.error("WebSocket error:", error);
    };

    ws.onclose = function (event) {
        console.log("WebSocket closed:", event);
        if (reconnectAttempts < maxReconnectAttempts) {
            const delay = baseReconnectDelay * Math.pow(2, reconnectAttempts);
            console.log(`Reconnecting in ${delay}ms... (Attempt ${reconnectAttempts + 1})`);
            setTimeout(() => {
                reconnectAttempts++;
                ws = initializeWebSocket(studentId, clientId);
            }, delay);
        } else {
            console.error("Max reconnection attempts reached. Please refresh or sign in again.");
            alert("Connection lost. Please try signing in again.");
            window.location.href = "../index.html";
        }
    };

    ws.onopen = function () {
        console.log("WebSocket connected successfully");
        reconnectAttempts = 0;
    };

    return ws;
}

document.addEventListener("DOMContentLoaded", () => {
    let clientId = Date.now();

    let studentId = sessionStorage.getItem("studentId");
    if (!studentId) {
        alert("Signed out, try to sign in again");
        window.location.href = "../index.html";
        return;
    }

    let ws = initializeWebSocket(studentId, clientId);

    document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "visible" && ws.readyState === WebSocket.CLOSED) {
            console.log("Page visible, attempting to reconnect WebSocket...");
            ws = initializeWebSocket(studentId, clientId);
        }
    });
});

function setNotifications(message){
    let val = JSON.parse(sessionStorage.getItem('myItem'));
    if(val){
        console.warn(val);
        if(val.length >= 3){
            val.shift();
        }     
    }
    else {
        val = [];
    }
    val.push(message);

    sessionStorage.setItem('myItem', JSON.stringify(val));
    showNotifications(); 
}


function showNotifications(){
    let val = JSON.parse(sessionStorage.getItem('myItem'));
    
    let dropdown_message = document.getElementsByClassName("dropdown_messages")[0];
    if(!dropdown_message){
        return;
    }
    dropdown_message.innerHTML = ``;
    if(val){
        console.warn(val);
    val.forEach(element => {
        let new_notification = document.createElement("div");
        new_notification.classList.add("message");
        let message = element.message;
        if (element.message.length > 15){
            message = element.message.slice(0,15);
            message += "...";
        }
        new_notification.innerHTML = `
        <img class="user_icon" alt="User_icon" src="../src/user.png" />
        <div class="message_text">
            <p>${element.first_name + " " + element.last_name + ""}</p>
            <p>${message}</p>
        </div>
        `;
        dropdown_message.appendChild(new_notification);
        })
    toggleBellAnimation();
    }
    else{
        dropdown_message.innerHTML = `No messages`
    }

}
