import json
import os
import torch
from diffusers import Flux2KleinKVPipeline
from diffusers import Flux2KleinPipeline
from optimum.quanto import freeze, qfloat8, quantize
import tkinter as tk
from tkinter import ttk  # serve per Combobox
from tkinterdnd2 import DND_FILES, TkinterDnD  # libreria corretta per il drag & drop
from PIL import Image, ImageTk
 
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from deep_translator import GoogleTranslator
import torch


# Caricamento del modello NLLB solo quando serve
nllb_model = None
nllb_tokenizer = None


def traduci(text="una bella ragazza giovane", org="ita", dest="eng"):

    global nllb_model, nllb_tokenizer

    # ==========================================================
    # CODICI DEEP TRANSLATOR / GOOGLE
    # ==========================================================

    google_lang_map = {
        "ita": "it",
        "eng": "en",
        "fra": "fr",
        "deu": "de",
        "spa": "es",
        "por": "pt",
    }

    # ==========================================================
    # CODICI NLLB
    # ==========================================================

    nllb_lang_map = {
        "ita": "ita_Latn",
        "eng": "eng_Latn",
        "fra": "fra_Latn",
        "deu": "deu_Latn",
        "spa": "spa_Latn",
        "por": "por_Latn",
    }

    google_src = google_lang_map.get(org, org)
    google_dest = google_lang_map.get(dest, dest)

    src_lang = nllb_lang_map.get(
        org,
        f"{org}_Latn"
    )

    dest_lang = nllb_lang_map.get(
        dest,
        f"{dest}_Latn"
    )

    # ==========================================================
    # 1. DEEP TRANSLATOR
    # ==========================================================

    try:

        translated = GoogleTranslator(
            source=google_src,
            target=google_dest
        ).translate(text)

        if translated and translated.strip():

            print("Traduzione effettuata con Deep Translator.")

            return translated

    except Exception as e:

        print(f"Deep Translator fallito: {e}")

    # ==========================================================
    # 2. FALLBACK NLLB LOCALE
    # ==========================================================

    print("Deep Translator non disponibile.")
    print("Utilizzo NLLB-200 locale...")

    model_name = "facebook/nllb-200-distilled-600M"

    try:

        # ------------------------------------------------------
        # Carica NLLB solamente la prima volta
        # ------------------------------------------------------

        if nllb_tokenizer is None or nllb_model is None:

            print("Caricamento NLLB-200...")

            nllb_tokenizer = AutoTokenizer.from_pretrained(
                model_name
            )

            nllb_model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name
            )

            nllb_model.eval()

            print("NLLB-200 caricato.")

        # ------------------------------------------------------
        # Lingua sorgente
        # ------------------------------------------------------

        nllb_tokenizer.src_lang = src_lang

        # ------------------------------------------------------
        # Tokenizzazione
        # ------------------------------------------------------

        inputs = nllb_tokenizer(
            text,
            return_tensors="pt"
        )

        # ------------------------------------------------------
        # Generazione
        # ------------------------------------------------------

        with torch.no_grad():

            translated_tokens = nllb_model.generate(
                **inputs,

                forced_bos_token_id=
                    nllb_tokenizer.convert_tokens_to_ids(
                        dest_lang
                    ),

                max_length=1000
            )

        # ------------------------------------------------------
        # Decodifica
        # ------------------------------------------------------

        result = nllb_tokenizer.batch_decode(
            translated_tokens,
            skip_special_tokens=True
        )[0]

        print("Traduzione effettuata con NLLB locale.")

        return result

    except Exception as e:

        print(f"Errore NLLB: {e}")

        # ------------------------------------------------------
        # Se anche NLLB fallisce
        # ------------------------------------------------------

        print("Restituisco il testo originale.")

        return text


# FIX: img1/img2/img3/img4 a volte arrivano come path (stringa) e a volte come
# oggetti PIL.Image già aperti dal chiamante. os.path.exists() richiede una stringa/path,
# quindi va chiamato solo se il valore è effettivamente una stringa (o os.PathLike).
def _e_path(v):
    """
    Restituisce True se v è un percorso file valido come tipo.
    """

    return isinstance(
        v,
        (str, bytes, os.PathLike)
    )


def _carica_immagine(v):
    """
    Accetta:
        - None
        - percorso immagine
        - PIL.Image.Image

    Restituisce sempre una PIL.Image RGB oppure None.
    """

    if v is None:
        return None

    # -----------------------------------------------------
    # Immagine PIL già caricata
    # -----------------------------------------------------

    if isinstance(v, Image.Image):

        return v.convert("RGB")

    # -----------------------------------------------------
    # Percorso file
    # -----------------------------------------------------

    if _e_path(v):

        try:

            if os.path.exists(v):

                with Image.open(v) as img:

                    return img.convert("RGB").copy()

        except Exception as e:

            print(
                f"Errore apertura immagine "
                f"'{v}': {e}"
            )

            return None

    return None

def flux2(
    img1=None, img2=None, img3=None, img4=None,
    path1=None, path2=None, path3=None, path4=None,
    prompt=None,
    steps=8,
    lora1=None, lora2=None,
    outname="output",
):
    print("""Genera un'immagine con FLUX.2 Klein usando fino a 4 immagini di riferimento
    (o 3 + sfondo in modalità LOCATION) e fino a 2 LoRA combinate.
     """)

    global path_stanza_corrente, use_location_var

    print("\n" + "=" * 70)
    print("                         FLUX 2")
    print("=" * 70)

    # ==========================================================
    # CONFIGURAZIONE
    # ==========================================================

    device = "cuda"
    dtype = torch.bfloat16
    model_path = "black-forest-labs/FLUX.2-klein-9B"

    # ==========================================================
    # INFORMAZIONI INPUT
    # ==========================================================

    print("\n---------- INPUT ----------")

    print("\nPATH ORIGINALI:")
    print(f"img1 : {path1 if path1 else 'NESSUNA'}")
    print(f"img2 : {path2 if path2 else 'NESSUNA'}")
    print(f"img3 : {path3 if path3 else 'NESSUNA'}")
    print(f"img4 : {path4 if path4 else 'NESSUNA'}")

    print("\nOGGETTI PIL:")
    print(f"img1 : {img1}")
    print(f"img2 : {img2}")
    print(f"img3 : {img3}")
    print(f"img4 : {img4}")

    print("\nLORA:")
    print(f"lora1 : {lora1}")
    print(f"lora2 : {lora2}")

    print(f"\noutput: {outname}")

    # ==========================================================
    # CARICAMENTO PIPELINE
    # ==========================================================

    print("\n---------- MODELLO ----------")
    print(f"Caricamento: {model_path}")

    pipe = Flux2KleinPipeline.from_pretrained(model_path, dtype=dtype)

    print("Pipeline caricata.")

    # ==========================================================
    # LORA (caricamento + attivazione combinata)
    # ==========================================================

    print("\n---------- LORA ----------")

    adapters_attivi = []
    pesi_attivi = []

    if lora1 and os.path.exists(lora1):
        pipe.load_lora_weights(lora1, adapter_name="lora1")
        adapters_attivi.append("lora1")
        pesi_attivi.append(0.8)
        print(f"LoRA 1 caricata: {lora1} (peso 0.8)")
    elif lora1:
        print(f"ATTENZIONE: LoRA 1 non trovata: {lora1}")

    if lora2 and os.path.exists(lora2):
        pipe.load_lora_weights(lora2, adapter_name="lora2")
        adapters_attivi.append("lora2")
        pesi_attivi.append(0.6)
        print(f"LoRA 2 caricata: {lora2} (peso 0.6)")
    elif lora2:
        print(f"ATTENZIONE: LoRA 2 non trovata: {lora2}")

    if adapters_attivi:
        # Attivazione in un'unica chiamata: necessario per usare più LoRA insieme,
        # perché set_adapters() successivi sovrascrivono l'attivazione precedente.
        pipe.set_adapters(adapters_attivi, adapter_weights=pesi_attivi)
        print(f"Adapter attivi: {adapters_attivi} con pesi {pesi_attivi}")
    else:
        print("Nessuna LoRA attiva.")

    # ==========================================================
    # QUANTIZZAZIONE
    # ==========================================================

    print("\n---------- QUANTIZZAZIONE ----------")

    # quantize() modifica il modello direttamente.
    # NON assegnare il risultato a pipe.transformer/text_encoder.

    quantize(pipe.transformer, qfloat8)
    quantize(pipe.text_encoder, qfloat8)

    freeze(pipe.transformer)
    freeze(pipe.text_encoder)

    print("Transformer quantizzato.")
    print("Text encoder quantizzato.")

    # Nota: se il modello usa un secondo text encoder (es. pipe.text_encoder_2),
    # va quantizzato/congelato separatamente, altrimenti resta in dtype pieno:
    if hasattr(pipe, "text_encoder_2") and pipe.text_encoder_2 is not None:
        quantize(pipe.text_encoder_2, qfloat8)
        freeze(pipe.text_encoder_2)
        print("Text encoder 2 quantizzato.")

    # ==========================================================
    # CPU OFFLOAD
    # ==========================================================

    print("\n---------- VRAM ----------")

    pipe.enable_model_cpu_offload()

    print("Model CPU offload attivato.")

    # ==========================================================
    # DETERMINAZIONE MODALITÀ
    # ==========================================================

    try:
        use_location = bool(use_location_var.get())
    except Exception:
        use_location = bool(use_location_var)

    print("\n---------- MODALITÀ ----------")
    print(f"Modalità LOCATION: {'ATTIVA' if use_location else 'DISATTIVA'}")

    # ==========================================================
    # CARICAMENTO IMMAGINI
    # ==========================================================

    images = []

    print("\n---------- IMMAGINI ----------")

    def _aggiungi(nome, valore):
        """Carica, ridimensiona e aggiunge l'immagine alla lista se valida."""
        print(f"\n[{nome.upper()}]")
        print(f"Path/oggetto: {valore}")

        base = _carica_immagine(valore)

        if base is not None:
            base = ridimensiona_immagine(base)
            images.append(base)
            print(f"OK - {nome} caricata.")
            return True

        print(f"{nome} assente.")
        return False

    if use_location:
        # --------------------------------------------------
        # MODALITÀ LOCATION — Ordine: img1, sfondo, img2, img3
        # --------------------------------------------------

        _aggiungi("img1", img1)

        print("\n[SFONDO]")

        if path_stanza_corrente and os.path.exists(path_stanza_corrente):
            print(f"Path sfondo: {path_stanza_corrente}")

            try:
                with Image.open(path_stanza_corrente) as tmp:
                    img_sfondo = tmp.convert("RGB").copy()

                img_sfondo = ridimensiona_immagine(img_sfondo)
                images.append(img_sfondo)

                print("OK - sfondo caricato.")

            except Exception as e:
                print(f"ERRORE caricamento sfondo: {e}")
        else:
            print("Nessuno sfondo valido.")

        _aggiungi("img2", img2)
        _aggiungi("img3", img3)

    else:
        # --------------------------------------------------
        # MODALITÀ NORMALE — Ordine: img1, img2, img3, img4
        # --------------------------------------------------

        _aggiungi("img1", img1)
        _aggiungi("img2", img2)
        _aggiungi("img3", img3)
        _aggiungi("img4", img4)

    # ==========================================================
    # RIEPILOGO IMMAGINI
    # ==========================================================

    print("\n---------- RIEPILOGO IMMAGINI ----------")
    print(f"Numero immagini effettivamente caricate: {len(images)}")

    if not images:
        print("Nessuna immagine di riferimento.")
    else:
        for i, image in enumerate(images):
            print(f"images[{i}] -> {image.size[0]}x{image.size[1]}")

    # ==========================================================
    # DIMENSIONE OUTPUT
    # ==========================================================

    dimx, dimy = 1024, 1024

    print("\n---------- DIMENSIONE OUTPUT ----------")

    def _e_lora_clothes(lora_path):
        return (
            lora_path
            and os.path.exists(lora_path)
            and "clothesonoffv2" in os.path.basename(lora_path).split(".")[0]
        )

    if use_location and path_stanza_corrente and os.path.exists(path_stanza_corrente):
        # LOCATION + SFONDO
        dimx, dimy = 1300, 800

    elif not use_location and _e_lora_clothes(lora1):
        # NORMALE + LORA CLOTHES
        ref = _carica_immagine(img1)
        if ref is not None:
            dimx, dimy = ref.size

    elif use_location and _e_lora_clothes(lora1):
        # LOCATION + LORA CLOTHES
        ref = _carica_immagine(img2)
        if ref is not None:
            dimx, dimy = ref.size

    print(f"Output: {dimx} x {dimy}")

    # ==========================================================
    # PROMPT
    # ==========================================================

    print("\n---------- PROMPT ----------")

    # Supporto per: tk.Text, StringVar, stringa normale

    if isinstance(prompt, tk.Text):
        prompt_text = prompt.get("1.0", tk.END)
    elif hasattr(prompt, "get"):
        try:
            prompt_text = prompt.get()
        except Exception:
            prompt_text = str(prompt)
    elif prompt is None:
        prompt_text = ""
    else:
        prompt_text = str(prompt)

    prompt_text = prompt_text.strip()

    print("\nPrompt italiano:")
    print(prompt_text)

    prompt_eng = traduci(text=prompt_text, org="ita", dest="eng")

    print("\nPrompt inglese utilizzato da Flux:")
    print(prompt_eng)

    # ==========================================================
    # STEPS
    # ==========================================================

    if hasattr(steps, "get"):
        try:
            steps_val = int(steps.get())
        except Exception:
            steps_val = 8
    else:
        try:
            steps_val = int(steps)
        except Exception:
            steps_val = 8

    print("\n---------- GENERAZIONE ----------")
    print(f"Steps: {steps_val}")
    print(f"Risoluzione: {dimx} x {dimy}")
    print(f"Numero immagini reference: {len(images)}")
    print(f"Seed: 0")

    # ==========================================================
    # PREPARAZIONE IMAGE INPUT
    # ==========================================================

   
   
    print("\nGenerating...")

    try:
        generator = torch.Generator(device=device).manual_seed(0)
        os.makedirs("debug_input", exist_ok=True)

        if images is None:
            print("\n[DEBUG] image_input è None (text-to-image, nessun riferimento salvato).")

        elif isinstance(images, list):
            print(f"\n[DEBUG] image_input è una lista di {len(images)} immagini:")
            for i, img_debug in enumerate(images):
                debug_path = f"debug_input/input_{i}.png"
                img_debug.save(debug_path)
                print(f"  -> salvata {debug_path} ({img_debug.size[0]}x{img_debug.size[1]})")

        else:
            debug_path = "debug_input/input_0.png"
            images.save(debug_path)
            print(f"\n[DEBUG] image_input è una singola immagine, salvata in {debug_path} ({images.size[0]}x{images.size[1]})")
        print(f"numero image : {len(images)}")
        if len(images) == 0:
            result = pipe(
                prompt=prompt_eng,
                height=dimy,
                width=dimx,
                num_inference_steps=steps_val,
                generator=generator,
            )
        else:
            result = pipe(
                prompt=prompt_eng,
                image=images[0] if len(images) == 1 else images,
                height=dimy,
                width=dimx,
                num_inference_steps=steps_val,
                generator=generator,
            )

        image = result.images[0]

    except Exception as e:
        print("\nERRORE DURANTE LA GENERAZIONE:")
        print(e)
        raise

    # ==========================================================
    # SALVATAGGIO
    # ==========================================================

    os.makedirs("outimage", exist_ok=True)

    if not os.path.splitext(outname)[1]:
        outname = f"{outname}.png"

    out_path = os.path.join("outimage", outname)
    image.save(out_path)

    # ==========================================================
    # RISULTATO
    # ==========================================================

    print("\n---------- RISULTATO ----------")
    print(f"Immagine salvata: {out_path}")
    print(f"Dimensione finale: {image.size}")
    print("=" * 70)
    print("                    GENERAZIONE COMPLETATA")
    print("=" * 70 + "\n")

    return image
    
# =========================================================
# INTERFACCIA GRAFICA
# =========================================================

BG_COLOR = "lightblue"

window = TkinterDnD.Tk()
window.config(bg=BG_COLOR)
window.attributes("-fullscreen", True)
window.title("multiprocess")
window.geometry("1100x800")

window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=1)

# Esci dal fullscreen con Esc, altrimenti la finestra resta bloccata
window.bind("<Escape>", lambda e: window.attributes("-fullscreen", False))

# Lista globale di BLOCCHI (ogni blocco è un dict con i suoi widget/dati)
blocchi = []
numero_righe = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LORA_DIR = os.path.join(BASE_DIR, "lora")
PRESETS_PATH = os.path.join(BASE_DIR, "presets_prompts.json")


def carica_preset_prompts():
    """Carica la lista dei preset (azione, prompt, nome_lora1, nome_lora2)
    dal file presets_prompts.json. Se il file manca o e' malformato,
    ritorna una lista minima con solo 'nolora' cosi' la GUI non si rompe."""
    default = [{"azione": "nolora", "prompt": "", "nome_lora1": "nolora", "nome_lora2": ""}]
    try:
        with open(PRESETS_PATH, "r", encoding="utf-8") as f:
            preset = json.load(f)
            if not isinstance(preset, list) or not preset:
                print(f"Attenzione: {PRESETS_PATH} non contiene una lista valida.")
                return default
            return preset
    except FileNotFoundError:
        print(f"Attenzione: file preset non trovato: {PRESETS_PATH}")
        return default
    except json.JSONDecodeError as e:
        print(f"Attenzione: errore nel parsing di presets_prompts.json: {e}")
        return default


def _risolvi_percorso_lora(nome_file):
    if not nome_file or nome_file == "nolora":
        return None
    if not nome_file.endswith(".safetensors"):
        nome_file += ".safetensors"
    return os.path.join(LORA_DIR, nome_file)


def _lista_file_lora():
    """Ritorna i nomi dei file presenti nella cartella lora/, da usare
    come valori del combobox 'Lora 2'. Se la cartella non esiste ancora,
    ritorna una lista vuota invece di far esplodere la GUI."""
    if not os.path.isdir(LORA_DIR):
        print(f"Attenzione: cartella lora non trovata: {LORA_DIR}")
        return []
    return [os.path.basename(l) for l in os.listdir(LORA_DIR)]


PRESETS = carica_preset_prompts()
PRESETS_BY_AZIONE = {p.get("azione", "nolora"): p for p in PRESETS}
NOMI_AZIONI = [p.get("azione", "nolora") for p in PRESETS]

def _sanitizza_nome_file(testo):
    """Sostituisce i caratteri non validi per un nome file su Windows."""
    invalidi = '<>:"/\\|?*'
    for ch in invalidi:
        testo = testo.replace(ch, "_")
    testo = testo.strip()
    return testo or "senza_nome"


def ridimensiona_immagine(img, lato=128):
    w, h = img.size
    if w > h:
        rw = lato
        rh = (lato * h) // w
    else:
        rh = lato
        rw = (lato * w) // h
    return img.resize((rw, rh), Image.BICUBIC)

path1, path2, path3, path4 = None, None, None, None


def drag_e_drop(event, blocco_dict, indice_canvas, path):
    """
    Gestisce il drag & drop di un'immagine.

    Salva:
        1. il PATH originale (nella variabile globale path1/path2/path3/path4)
        2. l'immagine PIL
        3. il nome base del file
    """
    global path1, path2, path3, path4

    canvas = event.widget

    # =====================================================
    # RECUPERO PATH
    # =====================================================

    percorsi = window.tk.splitlist(event.data)

    if not percorsi:
        return

    path = percorsi[0]

    print("\n---------- DRAG & DROP ----------")
    print(f"Immagine ricevuta: {path}")

    # =====================================================
    # CONTROLLO FILE
    # =====================================================

    if not os.path.isfile(path):
        print(f"ERRORE: file non trovato: {path}")
        return

    # =====================================================
    # APERTURA IMMAGINE
    # =====================================================

    try:
        img = Image.open(path).convert("RGB")
    except Exception as e:
        print(f"Impossibile aprire l'immagine: {e}")
        return

    # =====================================================
    # ANTEPRIMA
    # =====================================================

    img_ridotta = ridimensiona_immagine(img, 128)
    foto = ImageTk.PhotoImage(img_ridotta)

    canvas.delete("all")
    canvas.create_image(64, 64, image=foto)
    canvas.image = foto

    # =====================================================
    # NOME FILE
    # =====================================================

    nome_base_file = os.path.splitext(os.path.basename(path))[0]
    nome_base_file = _sanitizza_nome_file(nome_base_file)

    # =====================================================
    # SALVATAGGIO DATI NEL DICT
    # =====================================================

    blocco_dict["percorsi_immagini"][indice_canvas] = path
    blocco_dict["immagini"][indice_canvas] = img
    blocco_dict["nomi_immagini"][indice_canvas] = nome_base_file

    # =====================================================
    # SALVATAGGIO NELLA VARIABILE GLOBALE CORRISPONDENTE
    # =====================================================

    if indice_canvas == 0:
        path1 = path
    elif indice_canvas == 1:
        path2 = path
    elif indice_canvas == 2:
        path3 = path
    elif indice_canvas == 3:
        path4 = path

    # =====================================================
    # DEBUG
    # =====================================================

    print(f"Canvas: {indice_canvas}")
    print(f"PATH salvato: {path}")
    print(f"PIL salvata: {img.size}")
    print(f"Nome immagine: {nome_base_file}")
    print("----------------------------------\n")


def aggiungi_blocco_canvas():
    global numero_righe

    blocco_frame = tk.Frame(scrollable_frame, bg=BG_COLOR)
    blocco_frame.grid(row=numero_righe, column=0, sticky="w", padx=5, pady=10)

    blocco_dict = {
    "frame": blocco_frame,

    "canvases": [],

    # Immagini PIL reali utilizzate da Flux
    "immagini": [
        None,
        None,
        None,
        None
    ],

    # PATH ORIGINALI dei file
    "percorsi_immagini": [
        None,
        None,
        None,
        None
    ],

    # Nome file senza estensione
    "nomi_immagini": [
        None,
        None,
        None,
        None
    ],

    "combobox_lora": [],

    "prompt_widget": None,

    "lora_paths": [
        None,
        None
    ],

    "azioni": [
        None,
        None
    ],
    }

    colori_canvas = ["red", "pink", "blue", "green"]
    for col in range(4):
        canvas = tk.Canvas(
            blocco_frame,
            width=128,
            height=128,
            bg=colori_canvas[col],
            highlightthickness=1,
            highlightbackground="black",
        )
        canvas.grid(row=0, column=col, rowspan=2, padx=5, pady=5)
        canvas.create_text(64, 64, text=f"Inserisci immagine {col}", fill="white")

        canvas.drop_target_register(DND_FILES)
        canvas.dnd_bind(
            "<<Drop>>",
            lambda event, b=blocco_dict, i=col: drag_e_drop(event, b, i, None),
        )

        blocco_dict["canvases"].append(canvas)

    # Il widget prompt va creato PRIMA delle combobox cosi' possiamo
    # riferirlo in modo sicuro dentro blocco_dict quando l'utente sceglie
    # un'azione dalla combobox Lora 1 / Lora 2.
    prompt = tk.Text(blocco_frame, width=35, height=6)
    prompt.grid(row=0, column=6, rowspan=2, padx=5, pady=5)
    prompt.insert("1.0", "inserisci un prompt")
    blocco_dict["prompt_widget"] = prompt

    # Valori aggiornati per i due combobox: Lora 1 prende sempre i
    # preset dal json, Lora 2 prende i file effettivamente presenti
    # nella cartella lora/ (letta ogni volta che si aggiunge un blocco,
    # cosi' se nel frattempo aggiungi un file nuovo compare comunque).
    # Per Lora 2 aggiungiamo in testa la voce "(nessuno)" per permettere
    # di non associare nessun lora a quello slot.
    NESSUN_LORA = "(nessuno)"
    nomi_lora_files = _lista_file_lora()

    for i in range(2):
        col = 4 + i

        label = tk.Label(blocco_frame, text=f"Lora {i + 1}", bg=BG_COLOR)
        label.grid(row=0, column=col, padx=5, pady=2, sticky="s")

        valori_combo = NOMI_AZIONI if i == 0 else ([NESSUN_LORA] + nomi_lora_files)

        combo = ttk.Combobox(blocco_frame, values=valori_combo, width=10, state="readonly")
        combo.grid(row=1, column=col, padx=5, pady=2, sticky="n")
        combo.set(valori_combo[0] if valori_combo else "")

        def _seleziona_lora(event=None, blocco=blocco_dict, indice=i, combo=combo):
            global use_location_var, x, y, matrice_stanze
            scelta = combo.get()

            if indice == 0:
                # Lora 1: comportamento originale, basato sui preset del json
                preset = PRESETS_BY_AZIONE.get(scelta)
                if preset is None:
                    return

                prompt_widget = blocco["prompt_widget"]
                prompt_widget.delete("1.0", "end")

                prompt_sfondi = {
                    's_camino': "image 2 di riferimento: salotto classico con divano in velluto bordeaux, tappeto persiano, quadri d'epoca, luce calda soffusa",
                    'f_camino': "image 2 di riferimento: camino acceso in mattoni, mensola con candele e orologio, tavolino con calici di vino, poltrona in pelle",
                    'd_camino': "image 2 di riferimento: credenza in legno scuro con vasi in porcellana bianca e blu, quadri floreali, poltrona bergère in pelle",

                    's_wc': "image 2 di riferimento: bagno elegante con vasca in marmo bianco e nero, rubinetteria dorata, schiuma e candela",
                    'f_wc': "image 2 di riferimento: wc con marmo bianco e nero a scacchiera, portarotolo e scopino dorati",
                    'd_wc': "image 2 di riferimento: wc visto di profilo con mobile lavabo scuro, top in marmo nero, rubinetteria oro",

                    's_camera': "image 2 di riferimento: letto matrimoniale vista laterale ampia, testiera capitonné beige, cuscini e piumone bianchi, quadro seppia, tenda beige, luce naturale",
                    'f_camera': "image 2 di riferimento: primo piano testiera capitonné imbottita a bottoni, cuscini bianchi soffici, piumone bianco, boiserie alla parete",
                    'd_camera': "image 2 di riferimento: letto matrimoniale visto di lato con testiera capitonné beige, cuscini bianchi, quadro seppia con veduta città, tenda drappeggiata",

                    's_salotto': "image 2 di riferimento: salotto raffinato con pareti color terracotta a boiserie, divano beige, poltrona viola in velluto, tende blu-verdi, camino in marmo, credenza con vasi in vetro colorato",
                    'f_salotto': "image 2 di riferimento: dettaglio ringhiera in ferro battuto nero a colonnine tornite, pavimento a scacchiera in marmo bianco e nero, parete color corallo",
                    'd_salotto': "image 2 di riferimento: salotto con pareti color corallo a boiserie, camino in marmo con TV, divano beige, tavolino in marmo nero e ottone, pavimento a scacchiera, ringhiera in ferro battuto",
                }

                try:
                    chiave = matrice_stanze[x][y]
                except (IndexError, TypeError):
                    chiave = None

                prompt_sfondo = prompt_sfondi.get(chiave, "image 2 di riferimento: sfondo stanza arredata con divano")

                # Prima il preset, poi (se richiesto) lo sfondo in coda.
                # NB: prompt_sfondo descrive l'immagine di sfondo che, nella lista
                # "images" passata alla pipeline, occupa la seconda posizione:
                # [image1, image_sfondo, image2, image3].
                prompt_widget.insert("1.0", preset.get("prompt", ""))
                if use_location_var.get():
                    prompt_widget.insert("end", "\n" + prompt_sfondo)

                nome_file_lora = preset.get("nome_lora1", "")
                blocco["lora_paths"][0] = _risolvi_percorso_lora(nome_file_lora)
                blocco["azioni"][0] = scelta
            else:
                # Lora 2: scelta diretta di un file dalla cartella lora/,
                # nessun preset/prompt associato. Se l'utente sceglie
                # "(nessuno)" (o non ha scelto nulla), lo slot resta vuoto.
                if scelta == NESSUN_LORA or not scelta:
                    blocco["lora_paths"][1] = None
                    blocco["azioni"][1] = None
                else:
                    blocco["lora_paths"][1] = _risolvi_percorso_lora(scelta)
                    blocco["azioni"][1] = os.path.splitext(scelta)[0]

        combo.bind("<<ComboboxSelected>>", _seleziona_lora)

        blocco_dict["combobox_lora"].append(combo)

    # --- Eliminazione blocco: definita UNA sola volta, fuori dal loop ---
    def elimina_blocco(blocco=blocco_dict):
        """Distrugge il frame del blocco e lo rimuove dalla lista globale."""
        blocco["frame"].destroy()
        if blocco in blocchi:
            blocchi.remove(blocco)
        scrollable_frame.update_idletasks()
        main_canvas.configure(scrollregion=main_canvas.bbox("all"))

    button_canc = tk.Button(
        blocco_frame,
        text="🗑 Elimina",
        width=10,
        height=3,
        bg="red",
        fg="white",
        command=elimina_blocco,
    )
    button_canc.grid(row=0, column=7, rowspan=2, padx=5, pady=5)

    blocchi.append(blocco_dict)

    numero_righe += 1

    scrollable_frame.update_idletasks()
    main_canvas.configure(scrollregion=main_canvas.bbox("all"))


# =========================================================
# LAYOUT PRINCIPALE: pesi/minsize per non schiacciare lo scroll
# =========================================================
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=1, minsize=480)  # colonna scroll blocchi
window.grid_columnconfigure(1, weight=2, minsize=500)  # colonna canvas stanza

# Struttura per lo scorrimento verticale + orizzontale
container = tk.Frame(window, bg=BG_COLOR, width=890, height=890)
container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
container.grid_propagate(False)  # mantiene 1024x1024 fisso, ignora la dimensione dei figli
container.grid_rowconfigure(0, weight=1)
container.grid_columnconfigure(0, weight=1)

main_canvas = tk.Canvas(container, bg=BG_COLOR)
scrollbar = tk.Scrollbar(container, orient="vertical", command=main_canvas.yview)
scrollbarx = tk.Scrollbar(container, orient="horizontal", command=main_canvas.xview)
scrollable_frame = tk.Frame(main_canvas, bg=BG_COLOR)

scrollable_frame.bind(
    "<Configure>",
    lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all")),
)

main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
main_canvas.configure(
    yscrollcommand=scrollbar.set,
    xscrollcommand=scrollbarx.set,
)

main_canvas.grid(row=0, column=0, sticky="nsew")
scrollbar.grid(row=0, column=1, sticky="ns")
scrollbarx.grid(row=1, column=0, sticky="ew")

def _scroll_verticale(event):
    main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

def _scroll_orizzontale(event):
    main_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")

main_canvas.bind_all("<MouseWheel>", _scroll_verticale)
main_canvas.bind_all("<Shift-MouseWheel>", _scroll_orizzontale)

# =========================================================
# COLONNA DESTRA: visualizzazione stanza + controlli direzionali
# =========================================================
frame_visual = tk.Frame(window, bg=BG_COLOR)
frame_visual.grid(row=0, column=1, sticky="nsew")
frame_visual.grid_rowconfigure(0, weight=1)   # la canvas occupa lo spazio verticale disponibile
frame_visual.grid_columnconfigure(0, weight=1)

dir_l = r"./location"

matrice_stanze = [
    ['s_camino', 'f_camino', 'd_camino'],
    ['s_wc', 'f_wc', 'd_wc'],
    ['s_camera', 'f_camera', 'd_camera'],
    ['s_salotto', 'f_salotto', 'd_salotto']
]

x, y = 3, 1  # stanza iniziale f_salotto (riga 3, colonna 1)

path_stanza_corrente = os.path.join(dir_l, matrice_stanze[x][y] + '.png')
print(f"stanza iniziale salotto: {path_stanza_corrente}")


def f_visualizza_stanza(event=None):
    global path_stanza_corrente, FRAME_v
    try:
        img_s = Image.open(path_stanza_corrente).convert('RGB')
    except Exception as e:
        print(f"Errore caricamento immagine: {e}")
        return

    canvas_w = FRAME_v.winfo_width() if FRAME_v.winfo_width() > 1 else 1024
    canvas_h = FRAME_v.winfo_height() if FRAME_v.winfo_height() > 1 else 630

    # Calcola le dimensioni mantenendo le proporzioni ORIGINALI dell'immagine,
    # scalando per riempire il più possibile la canvas senza deformarla
    ratio_img = img_s.width / img_s.height
    ratio_canvas = canvas_w / canvas_h

    if ratio_img > ratio_canvas:
        new_w = canvas_w
        new_h = int(canvas_w / ratio_img)
    else:
        new_h = canvas_h
        new_w = int(canvas_h * ratio_img)

    img_r = img_s.resize((new_w, new_h), Image.Resampling.BICUBIC)
    photo_img = ImageTk.PhotoImage(img_r)

    FRAME_v.delete("all")
    x_off = (canvas_w - new_w) // 2
    y_off = (canvas_h - new_h) // 2
    FRAME_v.create_image(x_off, y_off, anchor='nw', image=photo_img)
    FRAME_v.image = photo_img


def f_aggiorna_stanza():
    """Ricalcola il path in base a x,y correnti, aggiorna la label
    con il nome della location e ridisegna la canvas."""
    global path_stanza_corrente
    nome_stanza = matrice_stanze[x][y]
    path_stanza_corrente = os.path.join(dir_l, nome_stanza + '.png')
    print(f"stanza corrente: {path_stanza_corrente}")
    label_stanza.config(text=nome_stanza)
    f_visualizza_stanza()


def f_su():
    global x
    if x > 0:
        x -= 1
        f_aggiorna_stanza()


def f_giu():
    global x
    if x < len(matrice_stanze) - 1:
        x += 1
        f_aggiorna_stanza()


def f_sinistra():
    global y
    if y > 0:
        y -= 1
        f_aggiorna_stanza()


def f_destra():
    global y
    if y < len(matrice_stanze[x]) - 1:
        y += 1
        f_aggiorna_stanza()


# --- Canvas della stanza ---
FRAME_v = tk.Canvas(frame_visual, bg="red", width=1024, height=630)
FRAME_v.grid(row=0, column=0, sticky="ne")

FRAME_v.bind("<Configure>", f_visualizza_stanza)

# --- Frame indipendente per label, checkbox e controlli direzionali ---
frame_info_stanza = tk.Frame(frame_visual, bg=BG_COLOR)
frame_info_stanza.grid(row=1, column=0, pady=(4, 0))
# nota: niente sticky/columnspan legati alla colonna 0 di frame_visual,
# cosi' il frame si dimensiona solo in base al SUO contenuto (label+checkbox)
# e resta centrato come blocco unico, non "spalmato" sui 1024px della canvas

# --- Label con il nome della location corrente ---
label_stanza = tk.Label(
    frame_info_stanza,
    text=matrice_stanze[x][y],
    font=("Arial", 12, "bold"),
    bg=BG_COLOR,
    fg="black",
)
label_stanza.grid(row=0, column=0, sticky="e", padx=(0, 10))

# --- Checkbox "Usa Location" ---
use_location_var = tk.BooleanVar(value=False)  # True = di default la location e' attiva

check_use_location = tk.Checkbutton(
    frame_info_stanza,
    text="Usa Location",
    variable=use_location_var,
    bg=BG_COLOR,
    activebackground=BG_COLOR,
)
check_use_location.grid(row=0, column=1, sticky="w")

# --- Controlli direzionali, avvicinati alla canvas/label ---
frame_button = tk.Frame(frame_visual, bg=BG_COLOR)
frame_button.grid(row=2, column=0, sticky="n", pady=(4, 0))

STILE_DPAD = dict(font=("Arial", 11, "bold"), width=4, height=2,
                   bg="#607D8B", fg="white", activebackground="#455A64")

Button_su = tk.Button(frame_button, text="▲", command=f_su, **STILE_DPAD)
Button_su.grid(row=0, column=1, padx=2, pady=2)

Button_sinistra = tk.Button(frame_button, text="◀", command=f_sinistra, **STILE_DPAD)
Button_sinistra.grid(row=1, column=0, padx=2, pady=2)

Button_giu = tk.Button(frame_button, text="▼", command=f_giu, **STILE_DPAD)
Button_giu.grid(row=1, column=1, padx=2, pady=2)

Button_destra = tk.Button(frame_button, text="▶", command=f_destra, **STILE_DPAD)
Button_destra.grid(row=1, column=2, padx=2, pady=2)

# =========================================================
# Pulsanti / controlli in basso
# =========================================================
btn_frame = tk.Frame(window, bg=BG_COLOR)
btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

btn_aggiungi = tk.Button(
    btn_frame,
    text="➕ Aggiungi blocco",
    font=("Arial", 12, "bold"),
    bg="#4CAF50",
    fg="white",
    command=aggiungi_blocco_canvas,
)
btn_aggiungi.grid(row=0, column=0, padx=2, pady=5)

def f_genera():
    """
    Genera un'immagine per ciascun blocco.
    """

    print(
        "\n========== AVVIO GENERAZIONE ==========\n"
    )

    # =====================================================
    # CICLO BLOCCHI
    # =====================================================

    for idx, b in enumerate(blocchi):

        # -------------------------------------------------
        # IMMAGINI PIL
        # -------------------------------------------------

        img1, img2, img3, img4 = (
            b["immagini"]
        )

        # -------------------------------------------------
        # PATH ORIGINALI
        # -------------------------------------------------

        path1, path2, path3, path4 = (
            b["percorsi_immagini"]
        )

        # -------------------------------------------------
        # ALTRI DATI
        # -------------------------------------------------

        prompt_widget = b[
            "prompt_widget"
        ]

        lora1, lora2 = b[
            "lora_paths"
        ]

        nome_image1 = (
            b["nomi_immagini"][0]
            or f"blocco_{idx}"
        )

        # -------------------------------------------------
        # AZIONI
        # -------------------------------------------------

        azioni_valide = [
            a
            for a in b["azioni"]
            if a and a != "nolora"
        ]

        azione = (
            "_".join(azioni_valide)
            if azioni_valide
            else "nolora"
        )

        # -------------------------------------------------
        # NOME OUTPUT
        # -------------------------------------------------

        outname = _sanitizza_nome_file(
            f"{nome_image1}_{azione}"
        )

        # =================================================
        # DEBUG BLOCCO
        # =================================================

        print(
            f"\n========== BLOCCO {idx} =========="
        )

        print(
            "\n---------- PATH IMMAGINI ----------"
        )

        print(
            f"img1 PATH = "
            f"{path1 if path1 else 'NESSUNA'}"
        )

        print(
            f"img2 PATH = "
            f"{path2 if path2 else 'NESSUNA'}"
        )

        print(
            f"img3 PATH = "
            f"{path3 if path3 else 'NESSUNA'}"
        )

        print(
            f"img4 PATH = "
            f"{path4 if path4 else 'NESSUNA'}"
        )

        print(
            "\n---------- OGGETTI PIL ----------"
        )

        print(
            f"img1 PIL = {img1}"
        )

        print(
            f"img2 PIL = {img2}"
        )

        print(
            f"img3 PIL = {img3}"
        )

        print(
            f"img4 PIL = {img4}"
        )

        print(
            "\n---------- ALTRI DATI ----------"
        )

        print(
            f"Prompt italiano = {prompt_widget}"
        )

        print(
            f"LORA 1 = {lora1}"
        )

        print(
            f"LORA 2 = {lora2}"
        )

        print(
            f"Output = {outname}"
        )

        # =================================================
        # FLUX
        # =================================================

        flux2(

            img1=img1,
            img2=img2,
            img3=img3,
            img4=img4,

            path1=path1,
            path2=path2,
            path3=path3,
            path4=path4,

            prompt=prompt_widget,

            steps=steps_scale,

            lora1=lora1,
            lora2=lora2,

            outname=outname,
        )


button_genera = tk.Button(
    btn_frame,
    text="Avvio Generazione",
    font=("Arial", 12, "bold"),
    bg="blue",
    fg="white",
    command=f_genera,
)
button_genera.grid(row=0, column=1, padx=2, pady=5)

lbl_steps = tk.Label(
    btn_frame, text="Steps: 8", font=("Arial", 12, "bold"), bg=BG_COLOR, fg="black"
)
lbl_steps.grid(row=0, column=3, padx=5, pady=5)


def f_step(val):
    valore_intero = int(float(val))
    lbl_steps.config(text=f"Steps: {valore_intero}")


steps_scale = tk.Scale(
    btn_frame, from_=1, to=50, orient="horizontal", command=f_step
)
steps_scale.set(8)
steps_scale.grid(row=0, column=4, padx=5, pady=5)


def f_close():
    window.destroy()

button_close = tk.Button(
    btn_frame,
    text="Close",
    font=("Arial", 12, "bold"),
    bg="red",
    fg="white",
    command=f_close,
)
button_close.grid(row=0, column=2, padx=2, pady=5)


aggiungi_blocco_canvas()

window.after(100, f_visualizza_stanza)

window.mainloop()