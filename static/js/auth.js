// Get DOM elements
const container = document.getElementById('container');
const signupBtn = document.getElementById('signup-btn');
const signinBtn = document.getElementById('signin-btn');

// Toggle forms
signupBtn?.addEventListener('click', () => {
  container.classList.add('change');
  history.replaceState(null, '', '?form=signup');
});

signinBtn?.addEventListener('click', () => {
  container.classList.remove('change');
  history.replaceState(null, '', '?form=signin');
});
