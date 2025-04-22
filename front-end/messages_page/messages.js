let chats = [];
let current_chat;
let users = [];
let chats_body = document.getElementsByClassName("chats")[0];
const send_button = document.getElementById("send-message");
let message_wrapper = document.getElementsByClassName("messages")[0];
let modal_add_member = document.getElementById("modal_member");
let btn_member = document.getElementById("btn_add_member");
let btn_chat = document.getElementById("button-room");
let input_area = document.getElementsByClassName("input-area")[0]
let close_add_member = document.getElementsByClassName("close")[0];
let input_search_block = document.getElementById("input-search-block") 
let members = document.getElementsByClassName("members-avatars")[0];


const inputHandler = function(e) {
    searchStudents(e.target.value)
}

input_search_block.addEventListener('input', inputHandler);

send_button.onclick = function(event) {
    if (window.location.pathname.includes("messages_page")) {
        let input = document.getElementById("input-area-block")
        let studentId = sessionStorage.getItem("studentId")
    if (!studentId) {
        alert("Signed out, try to sign in again");
        window.location.href = "../index.html";
        return;
    }
        if (input=="")
            return;
        const message = {
            message_type: "message",
            message: input.value,
            room_id: current_chat,
            user: studentId
        };
        console.log(message);
        ws.send(JSON.stringify(message));
        input.value = ''
        insertMessage(message);
        event.preventDefault();
    }
}
btn_chat.onclick = function(event) {
    users = []
    members.innerHTML = ``
    document.getElementById(current_chat).classList.remove("active");
    current_chat = "button-room";
    message_wrapper.innerHTML = ``
    document.getElementById("button-room").classList.add("active");
    showAddChat();
}
document.getElementById("input-area-block").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        event.preventDefault();
        send_button.click();
    }
});

document.addEventListener("DOMContentLoaded", fetchChats());
document.addEventListener("DOMContentLoaded", () => {sessionStorage.removeItem("myItem")});
async function fetchChats() {
    try {
        const response = await fetch(`http://localhost:8000/api/v1/message/user_chats/`+sessionStorage.getItem("studentId"), {
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
        chats = data.data;
        console.log(chats);
        
        chats.forEach(element => {
            let new_chat = document.createElement("div");
            new_chat.classList.add("chat-room")
            new_chat.id = element.id
            new_chat.innerHTML = element.chat_name;
            new_chat.onclick = selectChat;
            chats_body.appendChild(new_chat)
        });
        current_chat = chats[0].id;
        document.getElementById(current_chat).classList.add("active")
        await fetchChat(current_chat);
    } catch (error) {
        console.error("Error fetching chats:", error);
        if(error.message==401){
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";  
        }
        if(error.message==404){
            current_chat = "button-room";
            document.getElementById("button-room").classList.add("active");
            showAddChat();
        }
    }
}

async function fetchChat(chat_id){
    try {
        const response = await fetch(`http://localhost:8000/api/v1/message/chat/` + chat_id, {
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
        let i = 0;
        for(i = 0; i < chats.length; i++){
            if(chats[i].id == data.id){
                chats[i] = data;
                break;
            }
        }
        if(i == chats.length){
            let new_chat = document.createElement("div");
            new_chat.classList.add("chat-room")
            new_chat.id = data.id
            new_chat.innerHTML = data.chat_name;
            new_chat.onclick = selectChat;
            chats_body.appendChild(new_chat)
            chats.push(data);
        }
        console.log(data);
        if(chat_id == current_chat){
        insertMessages(data);
        }
    } catch (error) {
        console.error("Error fetching chats:", error);
        if(error.message==401){
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";  
        }
    }
}
function insertMessage(element){
    if ("room_id" in element){
        if (element.room_id != current_chat){
            return;
        }
    }
    let chat = chats.find(chat => {return chat.id == current_chat})
    let new_message = document.createElement("div");
    new_message.classList.add("message");
    let user = chat.users.find(user => {return user.id == Number(element.user)});
    let avatar_name = user.last_name + " " + user.first_name[0] + ".";
    if(element.user == sessionStorage.getItem("studentId")){
        new_message.classList.add("me");
        new_message.innerHTML=` 
            <div class="message-content">${element.message}</div>
                <div class="message-avatar">
                    <div class="avatar-circle"></div>
                    <span class="avatar-name">${avatar_name}</span>
            </div>
            `
    }
    else{
        new_message.classList.add("admin");
        new_message.innerHTML=` 
            <div class="message-avatar">
                <div class="avatar-circle"></div>
                <span class="avatar-name">${avatar_name}</span>
            </div>
            <div class="message-content">${element.message}</div>
            `
    }
    message_wrapper.appendChild(new_message);
    message_wrapper.scrollTo(0, message_wrapper.scrollHeight);
}

function insertUser(user){
    if (users.includes(user.id)) {
        alert("User is already in chat");
        return; 
    }
    users.push(user.id);
    let new_avatar = document.createElement("span");
    new_avatar.setAttribute("data-tooltip", user.last_name + " " + user.first_name[0] + ".");
    members.appendChild(new_avatar);
    
}

function insertUsers(users){
    members = document.getElementsByClassName("members-avatars")[0];
    members.innerHTML = ``;

    users.forEach(element => {
        insertUser(element)
    })
}

function insertMessages(chat){
    insertUsers(chat.users)
    document.getElementsByClassName("chat-header")[0].innerHTML = `${chat.chat_name}`
    message_wrapper.innerHTML = "";
    chat.messages.forEach(element => {insertMessage(element)})
}

function selectChat(e){
    input_area.style.display = "flex";
    let id = e.target.id;
    console.log(id);
    if (id == current_chat){
        return;
    }
    members.innerHTML = ``
    users = []
    document.getElementById("button-room").classList.remove("active");
    document.getElementById(current_chat).classList.remove("active");
    document.getElementById(id).classList.add("active");
    current_chat = id;
    fetchChat(current_chat)
}

async function selectChatFromMessages(id){
    console.log(id);
    if (id == current_chat){
        return;
    }
    members.innerHTML = ``
    users = [];
    await fetchChat(id);   
}

function showAddChat(){
    input_area.style.display = "none";
    let input_name = document.createElement("input");
    input_name.id = "input-chat-name";
    input_name.setAttribute("type", "text");
    input_name.setAttribute("placeholder", "Type your chat name");
    message_wrapper.appendChild(input_name);
    let buttons = document.createElement("div");
    let button_cancel = document.createElement("button");
    let button_create = document.createElement("button");
    button_cancel.classList.add("button_cancel");
    button_create.classList.add("button_create");
    button_cancel.innerHTML = `Cancel`;
    button_create.innerHTML = `Create`;
    button_cancel.onclick = function (){
        input_name.value = ``;
        users = [];
        members.innerHTML = ``;
    };
    button_create.onclick = function() {
        chatCreate(input_name);
    };
    buttons.appendChild(button_cancel);
    buttons.appendChild(button_create);
    message_wrapper.appendChild(buttons);
    document.getElementsByClassName("random");

}
function chatCreate(input_name){
    console.warn("here")
    if (input_name.value=="")
        return;
    const message = {
        message_type: "chat",
        chat_name: input_name.value,
        users: users
    };
    console.log(message);
    ws.send(JSON.stringify(message));
    input_name.value = ''
    users = [];
    members.innerHTML = ``;
}
btn_member.onclick = function(event) {
    modal_add_member.style.display = "block";
}
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
    if (input_search == ""){
        let student_warapper = document.getElementsByClassName("students_from_search")[0];
        student_warapper.innerHTML = ``;
        return
    }
    try {
        const response = await fetch(`http://localhost:8000/api/v1/student/search?input_search=${input_search}` , {
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
        let students = data.data;
        console.log(students)
        let student_warapper = document.getElementsByClassName("students_from_search")[0];
        student_warapper.innerHTML = ``;
        students.forEach((student) => {
            let new_student = document.createElement("div");
            new_student.classList.add("student_from_search");
            new_student.id = student.id;
            new_student.innerHTML = student.last_name + " " + student.first_name + " " + student.group;
            new_student.onclick = selectStudent;
            student_warapper.appendChild(new_student);

        });
    } catch (error) {
        // console.error("Error fetching students:", error);
        if(error.message==401){
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";  
        } 
        else if (error.message==404)
        {
            let student_warapper = document.getElementsByClassName("students_from_search")[0];
            student_warapper.innerHTML = ``;
        }
    }
}

function selectStudent(e){
    let id = e.target.id;
    console.warn(e.target.innerHTML);
    console.log(id);
    e.preventDefault();
    modal_add_member.style.display = "none";
    if (users.includes(id)) {
        alert("User is already in chat");
        return; 
    }
    if(current_chat == "button-room"){
        let fields = e.target.innerHTML.split(" ");
        let user = {
            last_name: fields[0],
            first_name: fields[1],
            id: id
        }
        insertUser(user)
    }
    else{
    const message = {
        message_type: "member",
        member_id: id,
        room_id: current_chat
    };
    ws.send(JSON.stringify(message));
    }
}
