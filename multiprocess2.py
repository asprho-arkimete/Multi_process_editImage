import json
import os
import tkinter as tk
from tkinter import ttk
from sympy.core.symbol import Boolean
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# Finestra principale
# ---------------------------------------------------------------------------
window = TkinterDnD.Tk()
window.geometry("1300x900")
window.resizable(False,False)
window.config(bg='gray')
window.grid_rowconfigure(0, weight=1)
window.grid_columnconfigure(0, weight=1)

raccoglitore_elementi = []   # tiene traccia di tutti gli elementi creati
contatore_elementi = [0]     # contatore per dare un nome/indice a ogni elemento

# ---------------------------------------------------------------------------
# Frame scorrevole (verticale + orizzontale) che conterra' tutti gli elementi
# ---------------------------------------------------------------------------
container = tk.Frame(window, bg='gray')
container.grid(row=0, column=0, sticky='nsew')
container.grid_rowconfigure(0, weight=1)
container.grid_columnconfigure(0, weight=1)
 
# ---------------------------------------------------------------------------
# Area di anteprima a destra, con il pannello delle frecce subito sotto
# ---------------------------------------------------------------------------

# sistema qui
dir_l = r"./location"

matrice_stanze = [
    ['s_camino', 'f_camino', 'd_camino'],
    ['s_wc', 'f_wc', 'd_wc'],
    ['s_camera', 'f_camera', 'd_camera'],
    ['s_salotto', 'f_salotto', 'd_salotto']
]

# Coordinate iniziali stanza corrente
x, y = 3, 1  # stanza iniziale f_salotto (riga 3, colonna 1)

def get_path_stanza(x, y):
    return os.path.join(dir_l, matrice_stanze[x][y] + '.png')

path_stanza_corrente = get_path_stanza(x, y)
print(f"stanza iniziale salotto: {path_stanza_corrente}")

def visualizza_stanza(event=None):
    global path_stanza_corrente, frame_visual
    img = Image.open(path_stanza_corrente)
    w = frame_visual.winfo_width()
    h = frame_visual.winfo_height()
    if w > 1 and h > 1:
        img = img.resize((w, h), Image.Resampling.BICUBIC)
        img_tk = ImageTk.PhotoImage(img)
        frame_visual.image = img_tk
        frame_visual.delete("all")
        frame_visual.create_image(w // 2, h // 2, image=img_tk)
        print(f"stanza corrente: {path_stanza_corrente} ({w}x{h})")

def cambia_stanza(dx, dy):
    global x, y, path_stanza_corrente
    nx, ny = x + dx, y + dy
    # Restringi alle coordinate valide della matrice (0-3, 0-2)
    if 0 <= nx < len(matrice_stanze) and 0 <= ny < len(matrice_stanze[0]):
        x, y = nx, ny
        path_stanza_corrente = get_path_stanza(x, y)
        visualizza_stanza()

frame_locations = tk.Frame(window, bg='green')
frame_locations.grid(row=0, column=1, sticky='nw', padx=10)
#1300*512:800*X
X=(512*800)//1300 
frame_visual = tk.Canvas(frame_locations, bg='red', width=512, height=X)
frame_visual.grid(row=0, column=0, sticky='nw', padx=10,pady=10)

frame_buttonf = tk.Frame(frame_locations, bg='green')
frame_buttonf.grid(row=1, column=0, columnspan=4, pady=5, sticky='ew')  # Use 'ew' to allow centering in column

# Imposta la colonna a espandersi così il frame occupa tutto lo spazio orizzontale
frame_locations.grid_columnconfigure(0, weight=1)
frame_buttonf.grid_columnconfigure((0,1,2,3), weight=1)

button_sin = tk.Button(frame_buttonf, bg='lightgray', text='Sinistra', 
                      command=lambda: cambia_stanza(0, -1))
button_sin.grid(row=0, column=0, padx=5)

button_su = tk.Button(frame_buttonf, bg='lightgray', text='Su', 
                     command=lambda: cambia_stanza(-1, 0))
button_su.grid(row=0, column=1, padx=5)

button_giu = tk.Button(frame_buttonf, bg='lightgray', text='Giù', 
                      command=lambda: cambia_stanza(1, 0))
button_giu.grid(row=0, column=2, padx=5)

button_destra = tk.Button(frame_buttonf, bg='lightgray', text='Destra', 
                         command=lambda: cambia_stanza(0, 1))
button_destra.grid(row=0, column=3, padx=5)

# Mostra subito la stanza iniziale
frame_visual.bind("<Configure>", visualizza_stanza)
 
canvas_scroll = tk.Canvas(container, bg='gray', highlightthickness=0)
vbar = tk.Scrollbar(container, orient='vertical', command=canvas_scroll.yview)
hbar = tk.Scrollbar(container, orient='horizontal', command=canvas_scroll.xview)
canvas_scroll.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

canvas_scroll.grid(row=0, column=0, sticky='nsew')
vbar.grid(row=0, column=1, sticky='ns')
hbar.grid(row=1, column=0, sticky='ew')

# frame_scroll e' il frame "vero", messo dentro al canvas: e' lui che
# conterra' fisicamente tutti gli elementi generati
frame_scroll = tk.Frame(canvas_scroll, bg='gray')
canvas_scroll.create_window((0, 0), window=frame_scroll, anchor='nw')


def on_frame_configure(event):
    # ogni volta che il frame interno cambia dimensione (es. aggiungo un
    # elemento), aggiorno la scrollregion cosi' le scrollbar sanno quanto
    # contenuto c'e' da scorrere
    canvas_scroll.configure(scrollregion=canvas_scroll.bbox('all'))


frame_scroll.bind('<Configure>', on_frame_configure)

# scroll con la rotellina del mouse (verticale) e Shift+rotellina (orizzontale)
def on_mousewheel(event):
    canvas_scroll.yview_scroll(int(-1 * (event.delta / 120)), 'units')


def on_shift_mousewheel(event):
    canvas_scroll.xview_scroll(int(-1 * (event.delta / 120)), 'units')


canvas_scroll.bind_all('<MouseWheel>', on_mousewheel)          # Windows/Mac
canvas_scroll.bind_all('<Shift-MouseWheel>', on_shift_mousewheel)
canvas_scroll.bind_all('<Button-4>', lambda e: canvas_scroll.yview_scroll(-1, 'units'))  # Linux
canvas_scroll.bind_all('<Button-5>', lambda e: canvas_scroll.yview_scroll(1, 'units'))   # Linux


# ---------------------------------------------------------------------------
# Costruzione di un singolo "elemento": 4 canvas drag&drop + combobox + testo
# ---------------------------------------------------------------------------
def crea_elemento(parent, indice):
    # stato proprio di QUESTO elemento (non globale, cosi' piu' elementi
    # non si pestano i piedi a vicenda)
    stato = {
        'path1': None, 'path2': None, 'path3': None, 'path4': None,
        'lora1_file': None,
        'loras1_files': [],
    }

    frame_elemento = tk.Frame(parent, bg='lightyellow', bd=2, relief='groove')
    frame_elemento.pack(fill='x', padx=10, pady=10, anchor='n')

    titolo = tk.Label(frame_elemento, text=f"Elemento {indice}",
                       bg='lightyellow', font=('Arial', 10, 'bold'))
    titolo.grid(row=0, column=0, columnspan=5, sticky='w', padx=5, pady=2)

    labels = {}  # per aggiornare la label del path dopo il drop

    def drag_drop(event, canvas, path_name):
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]

        canvas.delete('all')

        img = Image.open(file_path)
        w, h = img.size
        rw, rh = 128, 128
        if w >= h:
            rh = (rw * h) // w
        else:
            rw = (rh * w) // h

        img = img.resize((rw, rh), Image.Resampling.BICUBIC)
        photo = ImageTk.PhotoImage(img)

        canvas.create_image((64, 64), image=photo)
        canvas.image = photo  # riferimento, altrimenti il garbage collector la cancella

        stato[path_name] = file_path

        if path_name in labels:
            labels[path_name].config(text=f"{path_name}: {os.path.basename(file_path)}")

    canvasframe = tk.Frame(frame_elemento, bg='lightblue')
    canvasframe.grid(row=1, column=0, columnspan=5, sticky='w')

    colori = ['red', 'light green', 'light blue', 'pink']
    for i in range(4):
        path_name = f'path{i + 1}'
        c = tk.Canvas(canvasframe, bg=colori[i], width=128, height=128)
        c.create_text((64, 64), text=f'inserisci riferimento {i + 1}')
        c.grid(row=0, column=i, padx=5)
        c.drop_target_register(DND_FILES)
        c.dnd_bind('<<Drop>>', lambda event, cv=c, pn=path_name: drag_drop(event, cv, pn))
        lab = tk.Label(canvasframe, text=f"{path_name}: (nessun file)", bg='gray')
        lab.grid(row=1, column=i)
        labels[path_name] = lab

    strumenti = tk.Frame(frame_elemento, bg='lightblue')
    strumenti.grid(row=2, column=0, columnspan=5, sticky='w', pady=5)

    combomodel = ttk.Combobox(strumenti, values=['Flux2_k9b', 'Flux2k9b_kv', 'Flux2k9b_fp8'])
    combomodel.grid(row=0, column=0, padx=5)
    combomodel.set('Flux2_k9b')
    labm = tk.Label(strumenti, text='Models', bg='gray')
    labm.grid(row=1, column=0, padx=5)

    def load_lora1(event=None):
            with open("presets_prompts.json", encoding="utf-8") as file:
                data = json.load(file)
            azioni = [e['azione'] for e in data]
            stato['loras1_files'] = [e['nome_lora1'] for e in data]
            stato['prompts'] = [e['prompt'] for e in data]
            combolora1['values'] = azioni
    
    def select_lora1(event=None):
        # se per qualche motivo i preset non sono ancora stati caricati
        # (es. selezione via tastiera senza un click sulla combobox),
        # li carico adesso invece di andare in errore
        if not stato['prompts']:
            load_lora1()

        idx = combolora1.current()
        if idx == -1:
            return
        if idx >= len(stato['loras1_files']) or idx >= len(stato['prompts']):
            # combobox non allineata ai dati (json cambiato nel frattempo?)
            return

        azione = combolora1.get()
        if azione != 'nolora':
            stato['lora1_file'] = stato['loras1_files'][idx]
        else:
            stato['lora1_file'] = None

        # mostra nella text box il prompt del preset selezionato
        prompt_preset = stato['prompts'][idx]
        text_prompt.delete('1.0', 'end')
        text_prompt.insert('1.0', prompt_preset)

        print(f"[Elemento {indice}] lora1 selezionato: {stato['lora1_file']}")

    combolora1 = ttk.Combobox(strumenti, values=[])
    combolora1.grid(row=0, column=1, padx=5)
    combolora1.set('nolora')
    combolora1.bind('<Button-1>', load_lora1)
    combolora1.bind('<<ComboboxSelected>>', select_lora1)
    load_lora1()
    labl = tk.Label(strumenti, text='Lora1', bg='gray')
    labl.grid(row=1, column=1, padx=5)

    def load_lora2(event=None):
        lora_dir = 'lora'
        if not os.path.isdir(lora_dir):
            valori = ['nolora']
        else:
            valori = ['nolora']
            for fname in os.listdir(lora_dir):
                fullname = os.path.join(lora_dir, fname)
                if os.path.isfile(fullname) and not fname.startswith('.'):
                    valori.append(fname)
        combolora2['values'] = valori

    combolora2 = ttk.Combobox(strumenti, values=[])
    combolora2.grid(row=0, column=2, padx=5)
    combolora2.set('nolora')
    combolora2.bind('<Button-1>', load_lora2)
    load_lora2()
    labl2 = tk.Label(strumenti, text='Lora2', bg='gray')
    labl2.grid(row=1, column=2, padx=5)

    stato['var_sfondo'] = tk.BooleanVar(value=False)
    stato['path_sfondo'] = None

    def f_use():
        if stato['var_sfondo'].get():
            stato['path_sfondo'] = path_stanza_corrente
        else:
            stato['path_sfondo'] = None
        print(f"[Elemento {indice}] use sfondo: {stato['path_sfondo']}")

    use_sfondo = tk.Checkbutton(strumenti, text="usa sfondo",
                                 variable=stato['var_sfondo'], command=f_use)
    use_sfondo.grid(row=1, column=3, padx=5)


    text_prompt = tk.Text(frame_elemento, width=80, height=10)
    text_prompt.grid(row=3, column=0, columnspan=5, sticky='w', padx=5, pady=5)
    text_prompt.insert("1.0", "Inserisci un prompt")

    # salvo i riferimenti utili nello stato, cosi' puoi recuperarli dopo
    # (es. per leggere il prompt o i path quando l'utente genera l'immagine)
    stato['frame'] = frame_elemento
    stato['text'] = text_prompt
    stato['combomodel'] = combomodel
    stato['combolora1'] = combolora1
    stato['combolora2'] = combolora2

    return stato


def nuovo_elemento():
    contatore_elementi[0] += 1
    elemento = crea_elemento(frame_scroll, contatore_elementi[0])
    raccoglitore_elementi.append(elemento)


# crea un primo elemento di default all'avvio
nuovo_elemento()
# ---------------------------------------------------------------------------
frame_button2 = tk.Frame(window, bg='lightgreen')
frame_button2.grid(row=1, column=0, pady=10, sticky='nw')
 
aggiungi_nuovoElemento = tk.Button(frame_button2, text='Aggiungi Nuovo elemento', bg='#00ff90', command=nuovo_elemento)
aggiungi_nuovoElemento.grid(row=0, column=0, padx=5, sticky='w')
 
 
# ---------------------------------------------------------------------------
# Generazione: legge ogni elemento e passa i valori a flux2()
# ---------------------------------------------------------------------------

token='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'

import os
os.environ["HF_TOKEN"] = token
# Cartella dove si trova lo script
root = os.path.dirname(os.path.abspath(__file__))

os.environ["HF_HUB_DISABLE_XET"] = "1"
# NIENTE override di HF_HOME/TRANSFORMERS_CACHE:
# Flux2 e gli altri modelli HF useranno il percorso standard
# C:\Users\User\.cache\huggingface\hub

nltk_cache = os.path.join(root, ".cache", "nltk_data")

import nltk
nltk.data.path.append(nltk_cache)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', download_dir=nltk_cache)

from easynmt import EasyNMT
smallmodel='opus-mt'
medio_model='mbart50_en2m'
bigmodel='m2m_100_1.2B'
# EasyNMT resta nel percorso root, come richiesto
model = EasyNMT(f'{bigmodel}', cache_folder=os.path.join(root, ".cache", "easynmt"), resume=True)


import torch
from diffusers import Flux2KleinPipeline
from diffusers import Flux2KleinKVPipeline
from optimum.quanto import freeze, qfloat8, quantize
from deep_translator import GoogleTranslator
import math

nocloth="clothesonoffv2"
oldlora1=None
oldlora2=None
def flux2(raccoglitore_elementi):
    global nocloth, frame_visual,model
    device = "cuda"
    dtype = torch.bfloat16

    def f_resize(path):
        img = Image.open(path).convert("RGB")
        rw, rh = 128, 128
        w, h = img.size
        if w >= h:
            rh = (rw * h) // w
        else:
            rw = (rh * w) // h
        return img.resize((rw, rh), Image.Resampling.BICUBIC)
   
    def round_to_16(v):
        return max(16, math.ceil(v / 16) * 16)

    pipe = None
    current_model = None
    current_lora1 = None
    current_lora2 = None

    for i, elemento in enumerate(raccoglitore_elementi, start=1):
        ref_path1, ref_path2, ref_path3, ref_path4, model, lora1, lora2, prompt, path_sfondo = estrai_valori(elemento)
        print(f"--- Elemento {i} ---")
        print(f"ref_path1: {ref_path1}")
        print(f"ref_path2: {ref_path2}")
        print(f"ref_path3: {ref_path3}")
        print(f"ref_path4: {ref_path4}")
        print(f"model: {model}")
        print(f"lora1: {lora1}")
        print(f"lora2: {lora2}")
        print(f"prompt: {prompt}")
        print(f"path sfondo: {path_sfondo}")

        # --- Ricarica il modello SOLO se e' diverso da quello gia' in memoria ---
        if pipe is None or model != current_model:
            print(f"Carico modello: {model} (era: {current_model})")
            if model == "Flux2_k9b":
                pipe = Flux2KleinPipeline.from_pretrained(
                    "black-forest-labs/FLUX.2-klein-9B",dtype=dtype
                )
            elif model == "Flux2k9b_kv":
                pipe = Flux2KleinKVPipeline.from_pretrained(
                    "black-forest-labs/FLUX.2-klein-9b-kv", dtype=dtype
                )
            elif model == "Flux2k9b_fp8":
                pipe = Flux2KleinPipeline.from_single_file("flux-2-klein-9b-fp8.safetensors")
            else:
                raise ValueError(f"Modello non riconosciuto: {model!r}")

            print("QUANTIZZA TRASFORMER E TEXT ENCODER_2")
            quantize(pipe.transformer, weights=qfloat8)
            freeze(pipe.transformer)
            quantize(pipe.text_encoder, weights=qfloat8)
            freeze(pipe.text_encoder)
            
            pipe.enable_model_cpu_offload()

            current_model = model
            # modello nuovo => nessuna LoRA è ancora caricata su questa pipe
            current_lora1 = None
            current_lora2 = None
        else:
            print(f"Modello '{model}' invariato, riuso la pipe già in memoria")

        # --- Ricarica LoRA1 solo se diversa dalla precedente ---
        if lora1 != current_lora1:
            if current_lora1:  # c'era già un adapter con questo nome, va rimosso prima
                try:
                    pipe.delete_adapters("lora1")
                except Exception as e:
                    print(f"Avviso: impossibile rimuovere lora1 precedente: {e}")
            if lora1:
                path_lora1 = f"./lora/{lora1 if lora1.endswith('.safetensors') else lora1 + '.safetensors'}"
                print(f"Carico lora1: {path_lora1}")
                pipe.load_lora_weights(path_lora1, adapter_name='lora1')
            current_lora1 = lora1
        else:
            print(f"lora1 '{lora1}' invariata, nessun reload")

        # --- Ricarica LoRA2 solo se diversa dalla precedente ---
        if lora2 != current_lora2:
            if current_lora2:
                try:
                    pipe.delete_adapters("lora2")
                except Exception as e:
                    print(f"Avviso: impossibile rimuovere lora2 precedente: {e}")
            if lora2:
                path_lora2 = f"./lora/{lora2 if lora2.endswith('.safetensors') else lora2 + '.safetensors'}"
                print(f"Carico lora2: {path_lora2}")
                pipe.load_lora_weights(path_lora2, adapter_name='lora2')
            current_lora2 = lora2
        else:
            print(f"lora2 '{lora2}' invariata, nessun reload")

        # --- Attiva gli adapter correnti (va rifatto ogni volta, è economico) ---
        active_adapters, weights = [], []
        if current_lora1:
            active_adapters.append('lora1'); weights.append(0.8)
        if current_lora2:
            active_adapters.append('lora2'); weights.append(0.8)
        if active_adapters:
            pipe.set_adapters(active_adapters, adapter_weights=weights)

        # --- Costruzione lista immagini di riferimento ---
        images = []
        import os
        if path_sfondo and os.path.exists(path_sfondo):
            if ref_path1 and os.path.exists(ref_path1):
                print(f"Immagine 1 aggiunta al contenitore: {ref_path1}")
                images.append(f_resize(ref_path1))
            else:
                print(f"Immagine 1 non aggiunta al contenitore: {ref_path1}; error")
                images.append(None)

            print(f"Immagine 2 aggiunta al contenitore: {path_sfondo}")
            images.append(f_resize(path_sfondo))

            if ref_path2 and os.path.exists(ref_path2):
                print(f"Immagine 3 aggiunta al contenitore: {ref_path2}")
                images.append(f_resize(ref_path2))
            else:
                print(f"Immagine 3 non aggiunta al contenitore: {ref_path2}; error")
                images.append(None)

            if ref_path3 and os.path.exists(ref_path3):
                print(f"Immagine 4 aggiunta al contenitore: {ref_path3}")
                images.append(f_resize(ref_path3))
            else:
                print(f"Immagine 4 non aggiunta al contenitore: {ref_path3}; error")
                images.append(None)
        else:
            for idx, p in enumerate([ref_path1, ref_path2, ref_path3, ref_path4], start=1):
                if p and os.path.exists(p):
                    print(f"Immagine {idx} aggiunta al contenitore: {p}")
                    images.append(f_resize(p))
                else:
                    print(f"Immagine {idx} non aggiunta al contenitore: {p}; error")
                    images.append(None)

        dimx, dimy = 1024, 1024
        if lora1 and nocloth in lora1:
            img = Image.open(ref_path1)
            w, h = img.size
            if w >= h:
                dimy = (dimx * h) // w
            else:
                dimx = (dimy * w) // h
        elif path_sfondo and os.path.exists(path_sfondo):     
            dimx = round_to_16(1300)
            dimy = round_to_16(800)

        prompt_eng = None
        count = 0
        while prompt_eng is None and count < 10:
            #usa deep_translator per max 10 volte
            try:
                prompt_eng = GoogleTranslator(source='it', target='en').translate(prompt)
            except Exception as e:
                print(f"Traduzione fallita (tentativo {count + 1}): {e}")
            count += 1
        # se supera 10 volte ed è ancora None, usa model.translate
        if prompt_eng is None:
            prompt_eng = model.translate(prompt, source_lang='it', target_lang='en')
        #se è ancora none usa il prompt originale
        elif prompt_eng is None:
            prompt_eng = prompt
        if model == "Flux2k9b_kv":
            image = pipe(
                prompt=prompt_eng,
                height=dimy,
                width=dimx,
                num_inference_steps=8,
                generator=torch.Generator(device=device).manual_seed(0)
            ).images[0]
        else:
            image = pipe(
                prompt=prompt_eng,
                height=dimy,
                width=dimx,
                guidance_scale=1.0,
                num_inference_steps=8,
                generator=torch.Generator(device=device).manual_seed(0)
            ).images[0]
        # Correzione migliorata: salva nel percorso corretto e crea la cartella se non esiste
        import os

        base_name = os.path.splitext(os.path.basename(ref_path1))[0]
        lora_name = os.path.splitext(os.path.basename(lora1))[0] if lora1 else "nolora"
        out_dir = "./outimage"
        os.makedirs(out_dir, exist_ok=True)
        count_o = 1
        out_file = f"{base_name}_{lora_name}.png"
        path_out = os.path.join(out_dir, out_file)
        while os.path.exists(path_out):
            path_out = os.path.join(out_dir, f"{base_name}_{lora_name}_{count_o}.png")
            count_o += 1

        image.save(path_out)
        print(f"Immagine salvata in: {path_out}")
 
 
 
def estrai_valori(elemento):
    ref_path1 = elemento['path1']
    ref_path2 = elemento['path2']
    ref_path3 = elemento['path3']
    ref_path4 = elemento['path4']
    model = elemento['combomodel'].get()
    lora1 = elemento['lora1_file']
    lora2 = elemento['combolora2'].get()
    prompt = elemento['text'].get('1.0', 'end-1c')
    path_sfondo = elemento['path_sfondo']
    return ref_path1, ref_path2, ref_path3, ref_path4, model, lora1, lora2, prompt, path_sfondo
 
 
def f_generazione():
    print("avvia generazione")
    flux2(raccoglitore_elementi)
 
genera = tk.Button(frame_button2, text='Avvia generazione', bg='#46a5ff', command=f_generazione)
genera.grid(row=0, column=1, padx=5, sticky='w')

import threading as t
def f_frame_upscale():
    def avvio():
        os.system("python estrai_frame.py")
    t.Thread(target=avvio, daemon=True).start()  # correggi argomento: deam -> daemon

Frame_Upscale = tk.Button(frame_button2, text='Frame Upscale', bg='#ff67c4', command=f_frame_upscale)
Frame_Upscale.grid(row=0, column=2, padx=5, sticky='w')
 
window.mainloop()
 