document.addEventListener('DOMContentLoaded', () => {
    const modelSelect = document.getElementById('modelSelect');
    const STORAGE_KEY = 'selected_ai_model';

    // 1. Retrieve saved model from LocalStorage or fallback to 'gemini-2.5-flash'
    const savedModel = localStorage.getItem(STORAGE_KEY) || 'gemini-3.6-flash';
    modelSelect.value = savedModel;
    localStorage.setItem(STORAGE_KEY, savedModel); // Set default if missing

    // 2. Persist selection to LocalStorage whenever dropdown changes
    modelSelect.addEventListener('change', (event) => {
        const chosenModel = event.target.value;
        localStorage.setItem(STORAGE_KEY, chosenModel);
    });
});