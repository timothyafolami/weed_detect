document.getElementById("upload-form").addEventListener("submit", async function(event) {
    event.preventDefault();

    let formData = new FormData();
    formData.append("top_left", document.getElementById("top_left").value);
    formData.append("top_right", document.getElementById("top_right").value);
    formData.append("bottom_right", document.getElementById("bottom_right").value);
    formData.append("bottom_left", document.getElementById("bottom_left").value);
    formData.append("image", document.getElementById("image").files[0]);

    let response = await fetch("/upload-image/", {
        method: "POST",
        body: formData
    });

    if (response.ok) {
        let result = await response.json();
        document.getElementById("result").innerHTML = `
            <p>${result.message}</p>
            <a href="${result.download_url}" download>Download Shapefile ZIP</a>
        `;
    } else {
        document.getElementById("result").innerHTML = `<p>Upload failed.</p>`;
    }
});
