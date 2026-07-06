document.addEventListener('DOMContentLoaded', () => {
    
    // Pinterest Button Logic
    const pinBtn = document.getElementById('btn-pinterest');
    const pinStatusDot = document.getElementById('pin-status-dot');
    const pinStatusText = document.getElementById('pin-status-text');

    pinBtn.addEventListener('click', async () => {
        // UI Change to Loading state
        pinBtn.classList.add('loading');
        pinStatusDot.classList.remove('idle');
        pinStatusDot.classList.add('running');
        pinStatusText.textContent = 'Status: Running...';
        
        try {
            // Send request to n8n Webhook to log the run and trigger the bot
            const response = await fetch('http://localhost:5678/webhook/e47e3da6-d9da-416d-865c-bf04362b9f7f', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ bot: "pinterest", action: "run" })
            });
            
            if (response.ok) {
                // Keep it running visually, the bot might take a while
                // You can expand this logic later using websockets if you want live status updates
            } else {
                throw new Error('Server returned ' + response.status);
            }
        } catch (error) {
            console.error('Failed to trigger Pinterest bot:', error);
            // Optionally revert UI on failure
            // setTimeout(() => {
            //     pinBtn.classList.remove('loading');
            //     pinStatusDot.classList.remove('running');
            //     pinStatusDot.classList.add('idle');
            //     pinStatusText.textContent = 'Status: Error - Check Server';
            // }, 2000);
        }
    });

    // LinkedIn Button Logic
    const inBtn = document.getElementById('btn-linkedin');
    const inStatusDot = document.getElementById('in-status-dot');
    const inStatusText = document.getElementById('in-status-text');

    inBtn.addEventListener('click', async () => {
        inBtn.classList.add('loading');
        inStatusDot.classList.remove('idle');
        inStatusDot.classList.add('running');
        inStatusText.textContent = 'Status: Running...';
        
        try {
            const response = await fetch('http://localhost:5000/run/linkedin', {
                method: 'POST',
            });
            
            if (!response.ok) {
                throw new Error('Server returned ' + response.status);
            }
        } catch (error) {
            console.error('Failed to trigger LinkedIn bot:', error);
        }
    });

});
