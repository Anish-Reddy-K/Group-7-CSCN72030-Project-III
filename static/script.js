document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('.gallery img');

    images.forEach(function(image) {
        image.addEventListener('click', function() {
            window.open(this.src, '_blank');
        });
    });
});