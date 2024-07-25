document.addEventListener('DOMContentLoaded', () => {
    const ws = new WebSocket('ws://127.0.0.1:8000/ws');

    ws.onmessage = (event) => {
        const messageDiv = document.getElementById('message');
        messageDiv.innerHTML += `<p>${event.data}</p>`;
    };

    document.getElementById('uploadButton').addEventListener('click', async () => {
        const fileInput = document.getElementById('fileInput');
        if (fileInput.files.length === 0) {
            alert('Please select a file to upload.');
            return;
        }

        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('file', file);

        const progressBar = document.getElementById('uploadProgressBar');
        const progressContainer = document.getElementById('uploadProgress');
        const messageDiv = document.getElementById('message');

        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressBar.textContent = '0%';
        messageDiv.innerHTML = '';

        try {
            const response = await fetch('http://127.0.0.1:8000/upload_geotiff/', {
                method: 'POST',
                body: formData,
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (response.ok) {
                progressBar.style.width = '50%';
                progressBar.textContent = '50%';

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'weed_detections.zip';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);

                progressBar.style.width = '100%';
                progressBar.textContent = '100%';
                messageDiv.innerHTML = '<p>Weed detection complete. <a href="' + url + '" download="weed_detections.zip">Download the shapefile ZIP</a></p>';
            } else {
                messageDiv.innerHTML = '<p>Error uploading file: ' + response.statusText + '</p>';
            }
        } catch (error) {
            console.error('Error:', error);
            messageDiv.innerHTML = '<p>Error: ' + error.message + '</p>';
        }
    });
});
