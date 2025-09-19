document.addEventListener('DOMContentLoaded', () => {
  // Funções para o menu móvel
  const mobileMenuButton = document.querySelector('[aria-controls="mobile-menu"]');
  const mobileMenu = document.getElementById('mobile-menu');

  if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', () => {
      const isExpanded = mobileMenuButton.getAttribute('aria-expanded') === 'true';
      mobileMenuButton.setAttribute('aria-expanded', !isExpanded);
      mobileMenu.classList.toggle('hidden');
    });
  }

  // Funções para a seção de FAQ com accordion suave
  const faqButtons = document.querySelectorAll('[aria-controls^="faq-"]');

  faqButtons.forEach(button => {
    button.addEventListener('click', () => {
      const contentId = button.getAttribute('aria-controls');
      const content = document.getElementById(contentId);
      const isExpanded = button.getAttribute('aria-expanded') === 'true';
      const icon = button.querySelector('svg');

      button.setAttribute('aria-expanded', !isExpanded);
      
      if (isExpanded) {
        content.style.maxHeight = null;
        icon.classList.remove('rotate-180');
      } else {
        content.style.maxHeight = content.scrollHeight + "px";
        icon.classList.add('rotate-180');
      }
    });
  });

  const mobileSidebarToggle = document.getElementById('mobile-sidebar-toggle');
  const sidebar = document.getElementById('sidebar');

  if (mobileSidebarToggle && sidebar) {
    mobileSidebarToggle.addEventListener('click', () => {
      sidebar.classList.toggle('-translate-x-full');
    });
  }
});