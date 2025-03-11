function toggleBellAnimation() {
    const bell = document.querySelector('.bell_icon');
    bell.classList.add('swing');

    bell.addEventListener('animationend', function handler() {
        bell.classList.remove('swing');
        bell.removeEventListener('animationend', handler);
    });
}

var modal = document.getElementById("create");

var btn = document.getElementsByClassName("add")[0];

var span = document.getElementsByClassName("close")[0];

btn.onclick = function() {
    modal.style.display = "block";
}

span.onclick = function() {
    modal.style.display = "none";
}

window.onclick = function(event) {
if (event.target == modal) {
    modal.style.display = "none";
}
}

