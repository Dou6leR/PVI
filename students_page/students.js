let currentPage = 1;
let hasNextPage = false;
const paginationContainer = document.querySelector('.page-numbers');
const pagination_limit = 4;
let modal_create = document.getElementById("create");
let modal_delete = document.getElementById("delete_confirm");
let btn_add = document.getElementsByClassName("add")[0];
let btn_edit = document.querySelectorAll('.edit');
let btn_delete = document.querySelectorAll('.delete');
let span_create = document.getElementsByClassName("close")[0];
let cancel_create = document.getElementsByClassName("close_button_create")[0]
let span_delete = document.getElementsByClassName("close_delete")[0];
let submit_button = document.querySelector('.submit_button');
let tbody = document.querySelector('tbody');
let form_h2 = document.querySelector('.form_h2');
let headerCheckbox = document.querySelector('thead input[type="checkbox"]');
let bodyCheckboxes = document.querySelectorAll('tbody input[type="checkbox"]');

let currentMode = 'add';
let currentRow = null;


function bindEditHandler(btn) {
    btn.onclick = function(event) {
        event.preventDefault();
        currentRow = btn.closest('tr');
        if (!currentRow.querySelector('input[type="checkbox"]').checked){
            return;
        }
        form_h2.textContent = "Edit Student";
        submit_button.value = "Save";
        modal_create.style.display = "block";
        currentMode = 'edit';
        
        let cells = currentRow.getElementsByTagName('td');

        const groupSelect = document.getElementById('group');
        const fnameInput = document.getElementById('first_name');
        const lnameInput = document.getElementById('last_name');
        const genderSelect = document.getElementById('gender');
        const birthdayInput = document.getElementById('birthday');
        const form = document.getElementById('form');

        [fnameInput, lnameInput, birthdayInput, form].forEach(input => {
            input.classList.remove('error');
            const errorSpan = input.nextElementSibling;
            if (errorSpan && errorSpan.className === 'error-message') {
                errorSpan.remove();
            }
        });

        groupSelect.value = cells[1].textContent;
        let fullName = cells[2].textContent.split(' ');
        fnameInput.value = fullName[0];
        lnameInput.value = fullName[1] || '';
        genderSelect.value = cells[3].textContent === 'M' ? 'Male' : cells[3].textContent === 'F' ? 'Female' : 'Other';
        birthdayInput.value = cells[4].textContent.split('.').reverse().join('-');
    };
}


function bindDeleteHandler(btn) {
    btn.onclick = function() {
        const checkedBoxes = Array.from(bodyCheckboxes).filter(checkbox => checkbox.checked);
        currentRow = btn.closest('tr');
        if (!currentRow.querySelector('input[type="checkbox"]').checked){
            return;
        }

        const studentToDelete = document.getElementsByClassName("student_to_delete")[0];

        if (checkedBoxes.length === 1) {
            const row = checkedBoxes[0].closest('tr');
            const cells = row.getElementsByTagName('td');
            const fullName = cells[2].textContent;
            studentToDelete.textContent = fullName;
        } else {
            studentToDelete.textContent = "Multiple students";
        }

        modal_delete.style.display = "block";

        const confirmDelete = document.querySelector('.submit_button_delete');
        if (confirmDelete) {
            confirmDelete.onclick = function(event) {
                event.preventDefault(); 
                const allRows = document.querySelectorAll('tbody tr');
                allRows.forEach(row => {
                    if (row.querySelector('input[type="checkbox"]').checked) {
                        let id = parseInt((row.querySelector('input[type="checkbox"]').id.replace(/\D/g, "")), 10);
                        deleteStudent(id);
                    }
                });
                
                modal_delete.style.display = "none";
                bodyCheckboxes = document.querySelectorAll('tbody input[type="checkbox"]');
            };
        }

        const cancelDelete = document.querySelector('.close_button_delete');
        if (cancelDelete) {
            cancelDelete.onclick = function() {
                modal_delete.style.display = "none";
            };
        }
    };
}

function bindCheckboxHandler(checkbox) {
    checkbox.addEventListener('change', function() {
        headerCheckbox.checked = Array.from(bodyCheckboxes).every(cb => cb.checked);
    });
}

headerCheckbox.addEventListener('change', function() {
    bodyCheckboxes.forEach(function(checkbox) {
        checkbox.checked = headerCheckbox.checked;
    });
});

btn_edit.forEach(bindEditHandler);
btn_delete.forEach(bindDeleteHandler);
bodyCheckboxes.forEach(bindCheckboxHandler);


btn_add.onclick = function(event) {
    event.preventDefault();
    form_h2.textContent = "Add Student";
    submit_button.value = "Create";
    modal_create.style.display = "block";
    currentMode = 'add';

    const fname = document.getElementById('first_name');
    const lname = document.getElementById('last_name');
    const birthday = document.getElementById('birthday');
    const form = document.getElementById('form');
    [fname, lname, birthday, form].forEach(input => {
        input.classList.remove('error');
        const errorSpan = input.nextElementSibling;
        if (errorSpan && errorSpan.className === 'error-message') {
            errorSpan.remove();
        }
    });
    document.querySelector('form').reset();
};

function validateForm() {
    const group = document.getElementById('group').value;
    const fname = document.getElementById('first_name');
    const lname = document.getElementById('last_name');
    const gender = document.getElementById('gender').value;
    const birthday = document.getElementById('birthday');
    const form1 = document.getElementById("form");
    [fname, lname, birthday, form1].forEach(input => {
        input.classList.remove('error');
        const errorSpan = input.nextElementSibling;
        if (errorSpan && errorSpan.className === 'error-message') {
            errorSpan.remove();
        }
    });

    const nameRegex = /^[A-Za-zА-Яа-я]{2,}$/;
    const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
    
    let isValid = true;
    

    if (!nameRegex.test(fname.value)) {
        showError(fname, 'First name must be at least 2 only letters');
        isValid = false;
    }
    
    if (!nameRegex.test(lname.value)) {
        showError(lname, 'Last name must be at least 2 only letters');
        isValid = false;
    }
    
    if (!dateRegex.test(birthday.value) || !isValidDate(birthday.value)) {
        showError(birthday, 'Enter a valid date (age must be 16-100)');
        isValid = false;
    }
    
    const form = document.querySelector('form');
    if (!form.checkValidity()) {
        isValid = false;
    }

    return isValid;
}

function isValidDate(dateString) {
    const date = new Date(dateString);
    const today = new Date();
    const age = today.getFullYear() - date.getFullYear();
    return age >= 16 && age <= 100 && date <= today;
}

function showError(input, message) {
    input.classList.add('error');
    const errorSpan = document.createElement('span');
    errorSpan.className = 'error-message';
    errorSpan.textContent = message;
    const existingError = input.nextElementSibling;
    if (existingError && existingError.className === 'error-message') {
        existingError.remove();
    }

    input.parentNode.insertBefore(errorSpan, input.nextSibling);
}

submit_button.onclick = async function(event) {
    event.preventDefault();

    if (!validateForm()) {
        return;
    }

    let group = document.getElementById('group').value;
    let fname = document.getElementById('first_name');
    let lname = document.getElementById('last_name');
    let gender = document.getElementById('gender').value;
    let birthday = document.getElementById('birthday');
    let form1 = document.getElementById("form")

    const studentData = {
        group : group,
        first_name: fname.value,  
        last_name: lname.value,
        gender : gender,
        birthday: birthday.value,
    };

    student_json=JSON.stringify(studentData);
    console.log(student_json);
    try{
        if (currentMode === 'add') {
            await createStudent(student_json);
        } else if (currentMode === 'edit' && currentRow) {
            const id = parseInt((currentRow.querySelector('input[type="checkbox"]').id.replace(/\D/g, "")), 10);
            await updateStudent(id, student_json);
        }
        modal_create.style.display = "none";
    }
    catch (error) {
        [fname, lname, birthday, form1].forEach(input => {
            input.classList.remove('error');
            const errorSpan = input.nextElementSibling;
            if (errorSpan && errorSpan.className === 'error-message') {
                errorSpan.remove();
            }
        });
        if (error.detail && Array.isArray(error.detail)) {
            error.detail.forEach(function(field) {
                const fieldName = field.loc[field.loc.length - 1];
                const fieldElement = document.getElementById(fieldName);
                if (fieldElement) {
                    showError(fieldElement, field.msg);
                } else {
                    console.warn(`Field ${fieldName} not found in form`);
                    showError(form, field.msg);
                }
            });
        } else {
            console.error("Error student form:", error);
            
            if (error == "401") {
                alert("Signed out, try to sign in again");
                window.location.href = "../index.html";
            }
            showError(form, error.detail || "An unexpected error occurred");
        }
    } 
};

span_create.onclick = function(event) {
    event.preventDefault();
    modal_create.style.display = "none";
};

span_delete.onclick = function(event) {
    event.preventDefault();
    modal_delete.style.display = "none";
};

cancel_create.onclick = function(event) {
    event.preventDefault();
    modal_create.style.display = "none";
};

window.onclick = function(event) {
    if (event.target == modal_create) {
        event.preventDefault();
        modal_create.style.display = "none";
    }
};

window.onclick = function(event) {
    if (event.target == modal_delete) {
        event.preventDefault();
        modal_delete.style.display = "none";
    }
};

function updatePagination() {
    paginationContainer.innerHTML = '';
    
    const maxPagesToShow = 4;
    let startPage = Math.max(1, currentPage - Math.floor(maxPagesToShow / 2));
    let endPage = startPage + maxPagesToShow - 1;

    if (currentPage <= Math.floor(maxPagesToShow / 2)) {
        startPage = 1;
        endPage = Math.min(maxPagesToShow, currentPage + Math.floor(maxPagesToShow / 2));
    }

    if (!hasNextPage && tbody.children.length < pagination_limit) {
        endPage = currentPage;
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.textContent = i;
        if (i === currentPage) {
            pageBtn.classList.add('active');
        }
        pageBtn.addEventListener('click', () => {
            fetchStudents(i);
        });
        paginationContainer.appendChild(pageBtn);
    }

    document.querySelector('.prev-page').disabled = currentPage === 1;
    document.querySelector('.next-page').disabled = !hasNextPage;
}

document.querySelector('.prev-page').addEventListener('click', () => {
    if (currentPage > 1) {
        fetchStudents(currentPage - 1);
    }
});

document.querySelector('.next-page').addEventListener('click', () => {
    if (hasNextPage) {
        fetchStudents(currentPage + 1);
    }
});

document.addEventListener("DOMContentLoaded", fetchStudents(currentPage));
document.addEventListener("DOMContentLoaded", fetchUser);

async function fetchStudents(page) {
    try {
        const response = await fetch(`http://localhost:8000/api/v1/student/?offset=${(page-1)*pagination_limit}&limit=${pagination_limit + 1}`, {
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

        currentPage = page;

        hasNextPage = students.length > pagination_limit;
        
        if (hasNextPage) {
            students = students.slice(0, pagination_limit);
        }
        console.log(students);
        tbody.innerHTML = "";

        students.forEach((student) => {
            let new_row = document.createElement("tr");
            new_row.innerHTML = `
                <td>
                    <input type="checkbox" id="select${student.id}" name="select${student.id}" value="select${student.id}" />
                    <label for="select${student.id}">${student.id}</label>
                </td>
                <td>${student.group}</td>
                <td>${student.first_name} ${student.last_name}</td>
                <td>${student.gender.charAt(0)}</td>
                <td>${student.birthday.split('-').reverse().join('.')}</td>
                <td><span class="status ${student.status ? 'active' : 'inactive'}"></span></td>
                <td>
                    <button class="edit" data-id="${student.id}">✏️</button>
                    <button class="delete" data-id="${student.id}">✖</button>
                </td>
            `;
            new_row.querySelector('input[type="checkbox"]').checked = headerCheckbox.checked;
            tbody.appendChild(new_row);
            bodyCheckboxes = document.querySelectorAll('tbody input[type="checkbox"]');
            
            bindEditHandler(new_row.querySelector('.edit'));
            bindDeleteHandler(new_row.querySelector('.delete'));
            bindCheckboxHandler(new_row.querySelector('input[type="checkbox"]'));
        });
        updatePagination();
    } catch (error) {
        console.error("Error fetching students:", error);
        if(error.message==401){
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";  
        } 
    }
}

async function fetchUser() {
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/" + sessionStorage.getItem("studentId"),{
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
        username = document.querySelector(".username");
        username.innerHTML=data.first_name + " " + data.last_name;
    } catch (error) {
        console.error("Error fetching user:", error);
        if(error.message==401){
            alert("Signed out, try to sign in again");
            window.location.href = "../index.html";    
        }    
    }
}

document.querySelector(".sign_out").addEventListener("click", signOut);

async function signOut(event) {
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/logout", {
            method: "POST",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            }
        });
        if (response.ok) {
            const data = await response.json();
            sessionStorage.removeItem("credentials");
            sessionStorage.removeItem("studentId");
            window.location.href = "../index.html";
        }
    } catch (error) {
        console.error("Error during logout", error);
    }
}

async function createStudent(student_json) {
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/", {
            method: "POST",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            },
            body: student_json
        });

        if (response.ok) {
            fetchStudents(currentPage);
        } else {
            if(response.status == "401"){
                throw response.status;
            }
            else{
                const errorData = await response.json();
                throw errorData;
            }
            
        }
    } catch (error) {
        throw error;
    }
}

async function updateStudent(id, student_json) {
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/" + id, {
            method: "PATCH",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            },
            body: student_json
        });

        if (response.ok) {
            fetchStudents(currentPage);
        } else {
            if(response.status == "401"){
                throw response.status;
            }
            else{
                const errorData = await response.json();
                throw errorData;
            }      
        }
    } catch (error) {
        throw error;
    }
}

async function deleteStudent(id) {
    try {
        const response = await fetch("http://localhost:8000/api/v1/student/" + id, {
            method: "DELETE",
            headers: {
                "Authorization": "Basic " + sessionStorage.getItem("credentials"),
                "Content-Type": "application/json"
            },
        });

        if (response.ok) {
            fetchStudents(currentPage);
        } else {
            const errorData = await response.json();
            throw new Error(`Failed to update student: ${errorData.detail || response.statusText}`);
        }
    } catch (error) {
        console.error("Error deleting student:", error);
        throw error;
    }
}
