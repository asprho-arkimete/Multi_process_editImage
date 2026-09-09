# Multi_process_editImage

Elabora processi multipli di editing immagini su differenti soggetti e con differenti LoRA, utilizzando diversi modelli Flux (Klein 9B/KV, 4B). Include inoltre l'upscaling dei fotogrammi video e la possibilità di usare location predefinite o personalizzate per creare le tue foto, con preset di prompt per ogni LoRA associato.

## Requisiti

- Python 3.10
- GPU NVIDIA con supporto CUDA 13.0
- Git

## Installazione

1. Clona il repository:

   ```bash
   git clone https://github.com/asprho-arkimete/Multi_process_editImage.git
   cd Multi_process_editImage
   ```

2. Crea un ambiente virtuale:

   ```bash
   python -m venv vmulti
   ```

3. Attiva l'ambiente virtuale:

   **Windows (cmd/PowerShell):**
   ```bash
   vmulti\Scripts\activate
   ```

   **Linux/macOS:**
   ```bash
   source vmulti/bin/activate
   ```

4. Installa PyTorch con supporto CUDA:

   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu130
   ```

5. Installa le altre dipendenze:

   ```bash
   pip install -r requirements.txt
   ```

## Risorse da scaricare

- **Cartella LoRA**: scarica da [Hugging Face - Asprho/megalora](https://huggingface.co/Asprho/megalora/tree/main) ed estrai i file `.rar` nella cartella principale del progetto.
- **Location**: scarica la release `location.rar` dalla pagina [GitHub Releases](https://github.com/asprho-arkimete/Multi_process_editImage/releases/tag/imagelocations) e posizionala nella cartella principale del progetto.

## Avvio

```bash
python multiprocess2.py
```

