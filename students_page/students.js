let count = 2;
let modal_create = document.getElementById("create");
let modal_delete = document.getElementById("delete_confirm");
let btn_add = document.getElementsByClassName("add")[0];
let btn_edit = document.querySelectorAll('.edit');
let btn_delete = document.querySelectorAll('.delete');
let span_create = document.getElementsByClassName("close")[0];
let span_delete = document.getElementsByClassName("close_delete")[0];
let submit_button = document.querySelector('.submit_button');
let tbody = document.querySelector('tbody');
let form_h2 = document.querySelector('.form_h2');
let headerCheckbox = document.querySelector('thead input[type="checkbox"]');
let bodyCheckboxes = document.querySelectorAll('tbody input[type="checkbox"]');

let currentMode = 'add';
let currentRow = null;


function bindEditHandler(btn) {
    btn.onclick = function() {
        currentRow = btn.closest('tr');
        if (!currentRow.querySelector('input[type="checkbox"]').checked){
            return;
        }
        form_h2.textContent = "Edit Student";
        submit_button.textContent = "Save";
        modal_create.style.display = "block";
        currentMode = 'edit';
        
        let cells = currentRow.getElementsByTagName('td');

        const groupSelect = document.getElementById('group');
        const fnameInput = document.getElementById('fname');
        const lnameInput = document.getElementById('lname');
        const genderSelect = document.getElementById('gender');
        const birthdayInput = document.getElementById('birthday');
        
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
            confirmDelete.onclick = function() {
                const allRows = document.querySelectorAll('tbody tr');
                allRows.forEach(row => {
                    if (row.querySelector('input[type="checkbox"]').checked) {
                        row.remove();
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


btn_add.onclick = function() {
    form_h2.textContent = "Add Student";
    submit_button.textContent = "Create";
    modal_create.style.display = "block";
    currentMode = 'add';
    document.querySelector('form').reset();
};


submit_button.onclick = function(event) {
    event.preventDefault();

    let group = document.getElementById('group').value;
    let fname = document.getElementById('fname').value;
    let lname = document.getElementById('lname').value;
    let gender = document.getElementById('gender').value;
    let birthday = document.getElementById('birthday').value;

    let birthdayFormatted = birthday.split('-').reverse().join('.');

    if (!group || !fname || !lname || !gender || !birthday) {
        alert('Please fill in all fields!');
        return;
    }
    if (currentMode === 'add') {
        count++;
        var newRow = document.createElement('tr');
        newRow.innerHTML = `
            <td><input type="checkbox" checked
                    id="select${count}"
                    name="select${count}"
                    value="select${count}"
                />
                <label for="select${count}">${count}</label>
            </td>
            <td>${group}</td>
            <td>${fname} ${lname}</td>
            <td>${gender === 'Male' ? 'M' : gender === 'Female' ? 'F' : 'O'}</td>
            <td>${birthdayFormatted}</td>
            <td><span class="status inactive"></span></td>
            <td>
                <button class="edit">✏️</button>
                <button class="delete">✖</button>
            </td>
        `;
        newRow.querySelector('input[type="checkbox"]').checked = headerCheckbox.checked;
        tbody.appendChild(newRow);
        bodyCheckboxes = document.querySelectorAll('tbody input[type="checkbox"]');

        bindEditHandler(newRow.querySelector('.edit'));
        bindDeleteHandler(newRow.querySelector('.delete'));
        bindCheckboxHandler(newRow.querySelector('input[type="checkbox"]'));
    } else if (currentMode === 'edit' && currentRow) {

        var cells = currentRow.getElementsByTagName('td');
        cells[1].textContent = group;
        cells[2].textContent = `${fname} ${lname}`;
        cells[3].textContent = gender === 'Male' ? 'M' : gender === 'Female' ? 'F' : 'O';
        cells[4].textContent = birthdayFormatted;
    }
    modal_create.style.display = "none";
};

span_create.onclick = function() {
    modal_create.style.display = "none";
};

span_delete.onclick = function() {
    modal_delete.style.display = "none";
};

window.onclick = function(event) {
    if (event.target == modal_create) {
        modal_create.style.display = "none";
    }
};

window.onclick = function(event) {
    if (event.target == modal_delete) {
        modal_delete.style.display = "none";
    }
};
