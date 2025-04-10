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
