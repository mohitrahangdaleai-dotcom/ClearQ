// Add any custom JavaScript here
document.addEventListener('DOMContentLoaded', function() {
    // Auto-format skills input
    const skillsInput = document.getElementById('skills');
    if (skillsInput) {
        skillsInput.addEventListener('blur', function() {
            const skills = this.value.split(',')
                .map(skill => skill.trim())
                .filter(skill => skill.length > 0)
                .join(', ');
            this.value = skills;
        });
    }
    
    // Auto-format required skills input
    const requiredSkillsInput = document.getElementById('required_skills');
    if (requiredSkillsInput) {
        requiredSkillsInput.addEventListener('blur', function() {
            const skills = this.value.split(',')
                .map(skill => skill.trim())
                .filter(skill => skill.length > 0)
                .join(', ');
            this.value = skills;
        });
    }
    
    // Add confirmation for important actions
    const deleteButtons = document.querySelectorAll('.btn-danger');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('Are you sure you want to delete this?')) {
                e.preventDefault();
            }
        });
    });
    
    // Flash message auto-hide
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});