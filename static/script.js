document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const previewContainer = document.getElementById('preview-container');

    const mermaidSection = document.getElementById('mermaid-section');
    const mermaidPreview = document.getElementById('mermaid-preview');
    const downloadMermaidBtn = document.getElementById('download-mermaid-btn');
    const convertNsdBtn = document.getElementById('convert-to-nsd-btn');

    const nsdSection = document.getElementById('nsd-section');
    const svgPreview = document.getElementById('svg-preview');
    const downloadNsdBtn = document.getElementById('download-nsd-btn');

    const resetBtn = document.getElementById('reset-btn');

    let currentMermaidCode = '';
    let currentMermaidSvg = '';

    // Drag & Drop events
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // Click events
    browseBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFile(fileInput.files[0]);
        }
    });

    resetBtn.addEventListener('click', () => {
        previewContainer.classList.add('hidden');
        mermaidSection.classList.add('hidden');
        nsdSection.classList.add('hidden');
        dropZone.classList.remove('hidden');
        fileInput.value = '';
        mermaidPreview.innerHTML = '';
        svgPreview.innerHTML = '';
        currentMermaidCode = '';
        currentMermaidSvg = '';
    });

    downloadMermaidBtn.addEventListener('click', () => {
        if (currentMermaidSvg) {
            downloadStringAsFile(currentMermaidSvg, 'flowchart.svg', 'image/svg+xml');
        } else {
            downloadSvg(mermaidPreview, 'flowchart.svg');
        }
    });

    const downloadMmdBtn = document.getElementById('download-mmd-btn');
    downloadMmdBtn.addEventListener('click', () => {
        if (currentMermaidCode) {
            downloadStringAsFile(currentMermaidCode, 'flowchart.mmd', 'text/plain');
        }
    });

    downloadNsdBtn.addEventListener('click', () => {
        downloadSvg(svgPreview, 'structogram.svg');
    });

    convertNsdBtn.addEventListener('click', () => {
        if (!currentMermaidCode) return;

        const blob = new Blob([currentMermaidCode], { type: 'text/plain' });
        const file = new File([blob], "diagram.mmd", { type: "text/plain" });

        const formData = new FormData();
        formData.append('file', file);

        fetch('/convert', {
            method: 'POST',
            body: formData
        })
            .then(response => response.text())
            .then(svg => {
                nsdSection.classList.remove('hidden');
                svgPreview.innerHTML = svg;
                // Scroll to NSD section
                nsdSection.scrollIntoView({ behavior: 'smooth' });
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred during NSD conversion.');
            });
    });

    function handleFile(file) {
        const fileName = file.name.toLowerCase();

        if (fileName.endsWith('.py')) {
            // Convert Python to Mermaid
            const formData = new FormData();
            formData.append('file', file);

            fetch('/convert_python', {
                method: 'POST',
                body: formData
            })
                .then(response => response.text())
                .then(mermaidCode => {
                    renderMermaid(mermaidCode);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred during Python conversion.');
                });
        } else if (fileName.endsWith('.ino')) {
            // Convert Arduino to Mermaid
            const formData = new FormData();
            formData.append('file', file);

            fetch('/convert_arduino', {
                method: 'POST',
                body: formData
            })
                .then(response => response.text())
                .then(mermaidCode => {
                    renderMermaid(mermaidCode);
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('An error occurred during Arduino conversion.');
                });
        } else {
            // Assume Mermaid/Text file
            const reader = new FileReader();
            reader.onload = (e) => {
                renderMermaid(e.target.result);
            };
            reader.readAsText(file);
        }
    }

    async function renderMermaid(code) {
        currentMermaidCode = code;
        dropZone.classList.add('hidden');
        previewContainer.classList.remove('hidden');
        mermaidSection.classList.remove('hidden');
        nsdSection.classList.add('hidden'); // Hide NSD until requested

        mermaidPreview.innerHTML = '';
        currentMermaidSvg = '';

        try {
            // Check if code is valid mermaid?
            // mermaid.render needs an id
            const id = 'mermaid-graph-' + Date.now();
            // We can just insert text and let mermaid.init run? 
            // Better to use renderAsync or render.

            // Clean up code?
            // Sometimes code might have errors.

            const { svg } = await mermaid.render(id, code);
            mermaidPreview.innerHTML = svg;
            currentMermaidSvg = svg;
        } catch (error) {
            console.error('Mermaid rendering error:', error);
            mermaidPreview.innerHTML = `<p class="error">Error rendering Mermaid diagram: ${error.message}</p><pre>${code}</pre>`;
        }
    }

    function downloadStringAsFile(content, filename, type) {
        const blob = new Blob([content], { type: type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function downloadSvg(container, filename) {
        const svg = container.querySelector('svg');
        if (!svg) return;

        const svgData = new XMLSerializer().serializeToString(svg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
});
