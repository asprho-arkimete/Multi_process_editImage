import os
import tkinter as tk
from tkinter import HORIZONTAL, ttk
from tkinter import filedialog
from turtle import color
from PIL import Image, ImageTk
from moviepy import VideoFileClip
from tkinterdnd2 import DND_FILES, TkinterDnD

window = TkinterDnD.Tk()   # <-- classe corretta + parentesi per istanziare

window.title("Estrai Frame")
window.geometry("1600x1300")
window.configure(bg="gray")
window.resizable(False, False)

frame_frame = tk.Frame(window, bg="lightblue")
frame_frame.grid(row=0, column=0, sticky="nw", padx=10, pady=10)

canvas = tk.Canvas(frame_frame, bg="red", width=1204, height=800)
canvas.grid(row=0, column=0, sticky="nw")

path_image_ref = None
path_image_ref2 = None

# Manteniamo un riferimento globale alle immagini per evitare la garbage collection
img_tk_dict = {}

def f_resize_canvas(path, target_canvas):
    global img_tk_dict
    
    img_prev = Image.open(path)
    rw, rh = 128, 128
    w, h = img_prev.size
    
    if w >= h:
        rh = (rw * h) // w
    else:
        rw = (rh * w) // h

    img_prev = img_prev.resize((rw, rh), Image.Resampling.BICUBIC)
    
    # Crea l'immagine PhotoImage e salvala nel dizionario associato al canvas
    img_tk = ImageTk.PhotoImage(img_prev)
    img_tk_dict[target_canvas] = img_tk
    
    target_canvas.delete("all")
    target_canvas.create_image((64, 64), image=img_tk)
    target_canvas.image = img_tk  # Riferimento ulteriore per garbage collection
    target_canvas.update_idletasks()

    print(f"foto riferimento: {path} nella canvas:{target_canvas}")


def f_dragEdrop(event, target):
    """target: 'ref' -> aggiorna path_image_ref (canvas2)
       target: 'ref2' -> aggiorna path_image_ref2 (canvas3)"""
    global path_image_ref, path_image_ref2

    path_file = event.data.strip('{}')  # Rimuove le graffe se presenti (path con spazi)

    if target == 'ref':
        path_image_ref = path_file
        f_resize_canvas(path_image_ref, canvas2)
    else:
        path_image_ref2 = path_file
        f_resize_canvas(path_image_ref2, canvas3)


canvas2 = tk.Canvas(frame_frame, width=128, height=128, bg='violet')
canvas2.grid(row=0, column=1, sticky="nw", padx=10, pady=10)
canvas2.drop_target_register(DND_FILES)
canvas2.dnd_bind('<<Drop>>', lambda event: f_dragEdrop(event, 'ref'))

canvas3 = tk.Canvas(frame_frame, width=128, height=128, bg='pink')
canvas3.grid(row=0, column=2, sticky="nw", padx=10, pady=10)
canvas3.drop_target_register(DND_FILES)
canvas3.dnd_bind('<<Drop>>', lambda event: f_dragEdrop(event, 'ref2'))



points = []
point_ids = []
line_ids = []
dragging_index = None
R = 3
TOL = 6

img = None          # immagine PIL a piena risoluzione, correntemente mostrata
img_tk = None        # riferimento PhotoImage (evita garbage collection)
scale_x = 1.0        # fattore di conversione: pixel_canvas -> pixel_immagine_reale
scale_y = 1.0

file_path = None
video = None
fps = None
n_frame_max = 0

VIDEO_EXTS = (".mp4", ".avi", ".mov", ".mkv", ".webm")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".ico", ".webp")


def mostra_immagine(image):
    """Ridimensiona e disegna un'immagine PIL sul canvas.
       Salva anche l'immagine originale e la scala, necessarie per il crop."""
    global img, img_tk, scale_x, scale_y

    img = image  # <-- immagine ORIGINALE, piena risoluzione, usata dal crop

    w, h = image.size
    max_w, max_h = 800, 800
    scale = min(max_w / w, max_h / h)
    rw, rh = int(w * scale), int(h * scale)

    resized = image.resize((rw, rh))
    img_tk = ImageTk.PhotoImage(resized)

    canvas.configure(width=rw, height=rh)
    canvas.delete("all")
    canvas.create_image(0, 0, image=img_tk, anchor="nw")
    canvas.image = img_tk

    # il canvas viene ridimensionato esattamente sull'immagine mostrata,
    # quindi non c'è offset: l'immagine parte sempre da (0,0)
    scale_x = w / rw
    scale_y = h / rh

    reset_points()  # nuova immagine/frame = nuova selezione


def canvas_to_image_coords(x, y):
    """Converte un punto cliccato sul canvas nelle coordinate dell'immagine originale."""
    return x * scale_x, y * scale_y


def nearest_point_index(x, y):
    for i, (px, py) in enumerate(points):
        if abs(px - x) <= TOL and abs(py - y) <= TOL:
            return i
    return None


def redraw_polygon():
    global line_ids
    for lid in line_ids:
        canvas.delete(lid)
    line_ids = []
    n = len(points)
    for i in range(n - 1):
        lid = canvas.create_line(points[i][0], points[i][1],
                                  points[i + 1][0], points[i + 1][1], fill='blue')
        line_ids.append(lid)
    if n == 4:
        lid = canvas.create_line(points[3][0], points[3][1],
                                  points[0][0], points[0][1], fill='red')
        line_ids.append(lid)



def save_crop():
    global img, file_path, path_image_ref, points, canvas2
    
    if img is None:
        print("Nessuna immagine caricata: impossibile ritagliare.")
        return

    # Controlla che ci siano abbastanza punti selezionati
    if not points or len(points) < 2:
        print("Seleziona almeno 2 punti per definire l'area di ritaglio.")
        return

    # Converte i punti nelle coordinate dell'immagine originaria
    img_points = [canvas_to_image_coords(x, y) for (x, y) in points]

    xs = [p[0] for p in img_points]
    ys = [p[1] for p in img_points]
    
    # Arrotonda a interi
    left, upper = int(min(xs)), int(min(ys))
    right, lower = int(max(xs)), int(max(ys))

    # Verifica che la selezione abbia un'area valida (> 0 pixel)
    if left >= right or upper >= lower:
        print("Area di ritaglio non valida o di dimensione zero.")
        return

    # Ritaglio e salvataggio
    cropped = img.crop((left, upper, right, lower))

    os.makedirs("frame_ex", exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    path_out = f"frame_ex/crop_{base_name}.png"

    cropped.save(path_out)
    print(f"Salvato in {path_out}")

    path_image_ref = path_out
    
    # Passa sia il percorso che il canvas di destinazione
    f_resize_canvas(path_image_ref, canvas2)

def on_click(event):
    global dragging_index
    if not attiva_crop:
        return  # ignora i click se la modalità crop non è attiva

    x, y = event.x, event.y

    idx = nearest_point_index(x, y)
    if idx is not None:
        dragging_index = idx
        return

    if len(points) < 4:
        pid = canvas.create_oval(x - R, y - R, x + R, y + R, fill='red', outline='red')
        point_ids.append(pid)
        points.append((x, y))
        redraw_polygon()

        if len(points) == 4:
            save_crop()


def on_drag(event):
    if not attiva_crop or dragging_index is None:
        return
    if dragging_index is None:
        return
    x, y = event.x, event.y
    points[dragging_index] = (x, y)
    canvas.coords(point_ids[dragging_index], x - R, y - R, x + R, y + R)
    redraw_polygon()


def on_release(event):
    global dragging_index
    if dragging_index is not None and len(points) == 4:
        save_crop()
    dragging_index = None


def reset_points(event=None):
    global points, point_ids, line_ids
    for pid in point_ids:
        canvas.delete(pid)
    for lid in line_ids:
        canvas.delete(lid)
    points = []
    point_ids = []
    line_ids = []

hovered_index = None  # aggiungi questa globale insieme alle altre


def on_motion(event):
    global hovered_index
    x, y = event.x, event.y

    idx = nearest_point_index(x, y)

    if idx == hovered_index:
        return  # nessun cambiamento, niente da fare

    # ripristina il colore del punto precedentemente "illuminato"
    if hovered_index is not None:
        canvas.itemconfig(point_ids[hovered_index], fill='red', outline='red')

    # illumina di bianco il nuovo punto sotto il mouse
    if idx is not None:
        canvas.itemconfig(point_ids[idx], fill='white', outline='red')
        canvas.config(cursor='hand2')  # opzionale: cambia anche il cursore
    else:
        canvas.config(cursor='')

    hovered_index = idx


canvas.bind('<Motion>', on_motion)
canvas.bind('<Button-1>', on_click)
canvas.bind('<B1-Motion>', on_drag)
canvas.bind('<ButtonRelease-1>', on_release)
canvas.bind('<Button-3>', reset_points)


def f_load_image():
    global video, fps, n_frame_max, file_path
    print("Carica file video o immagine")
    file_path = filedialog.askopenfilename(
        filetypes=[("Immagini/Video",
                    "*.png *.jpg *.jpeg *.gif *.bmp *.tiff *.ico *.webp *.mp4 *.avi *.mov *.mkv *.webm")]
    )
    if not file_path:
        return

    if file_path.lower().endswith(IMAGE_EXTS):
        video = None
        n_frame_max = 0
        scorri_fotogrammi.config(to=0)
        scorri_fotogrammi.set(0)
        image = Image.open(file_path)
    elif file_path.lower().endswith(VIDEO_EXTS):
        video = VideoFileClip(file_path)
        fps = video.fps
        n_frame_max = int(video.duration * fps)
        scorri_fotogrammi.config(to=n_frame_max)
        scorri_fotogrammi.set(0)
        image = Image.fromarray(video.get_frame(0))
    else:
        print("Formato di file non supportato")
        return

    mostra_immagine(image)


Button_load = tk.Button(frame_frame, text="Carica File", command=f_load_image)
Button_load.grid(row=0, column=1, sticky="nw", padx=10, pady=10)


def f_estrai_frame():
    global video, scorri_fotogrammi, file_path

    if video is None:
        print("Nessun video caricato, impossibile estrarre il frame")
        return

    os.makedirs("frame_ex", exist_ok=True)

    frame_number = scorri_fotogrammi.get()
    t = frame_number / fps
    frame_array = video.get_frame(t)
    image = Image.fromarray(frame_array)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    path_out = f"./frame_ex/{base_name}_{frame_number}.png"

    k = 1
    while os.path.exists(path_out):
        path_out = f"./frame_ex/{base_name}_{frame_number}_{k}.png"
        k += 1
    image.save(path_out)
    print(f"Frame salvato in {path_out}")


estrai_fotogramma = tk.Button(frame_frame, text="Estrai frame", command=f_estrai_frame)
estrai_fotogramma.grid(row=0, column=2, sticky="nw", padx=10, pady=10)

attiva_crop = False


def f_crop():
    global attiva_crop
    attiva_crop = not attiva_crop  
    if attiva_crop:
        crop.config(bg='#2eff5f')
    else:
        crop.config(bg='#3842e9')
        reset_points()


crop = tk.Button(frame_frame, text='crop', bg='#3842e9', command=f_crop)  # <-- mancava command=f_crop
crop.grid(row=0, column=3, sticky="nw", padx=10, pady=10)  # <-- column=2 era già occupata da "estrai_fotogramma"


def f_upgrate_frame(valore):
    print("Aggiorna frame", valore)
    if video is not None:
        frame_number = int(valore)
        t = frame_number / fps  # get_frame vuole i secondi, non l'indice
        frame = video.get_frame(t)
        image = Image.fromarray(frame)
        mostra_immagine(image)
    else:
        print("Nessun video caricato")


def fpiu():
    if video is not None and scorri_fotogrammi.get() < n_frame_max:
        nuovo_valore = scorri_fotogrammi.get() + 1
        scorri_fotogrammi.set(nuovo_valore)
        f_upgrate_frame(nuovo_valore)


def fmeno():
    if video is not None and scorri_fotogrammi.get() > 0:
        nuovo_valore = scorri_fotogrammi.get() - 1
        scorri_fotogrammi.set(nuovo_valore)
        f_upgrate_frame(nuovo_valore)


scorri_fotogrammi = tk.Scale(frame_frame, from_=0, to=1000, orient="horizontal",
                              command=f_upgrate_frame, length=800)
scorri_fotogrammi.grid(row=1, column=0, sticky="nw", padx=10, pady=10)

button_meno = tk.Button(frame_frame, text="-", command=fmeno)
button_meno.grid(row=1, column=1, sticky="nw", padx=10, pady=10)

button_piu = tk.Button(frame_frame, text="+", command=fpiu)
button_piu.grid(row=1, column=2, sticky="nw", padx=10, pady=10)

token='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'

import os
import tkinter as tk
import torch
import nltk
from PIL import Image
from easynmt import EasyNMT
from diffusers import Flux2KleinPipeline
from optimum.quanto import freeze, qfloat8, quantize
from deep_translator import GoogleTranslator

# Assicurati che 'token' sia definito o importato
token = os.environ.get("HF_TOKEN", token)
os.environ["HF_TOKEN"] = token

# Cartella dove si trova lo script
root = os.path.dirname(os.path.abspath(__file__))

os.environ["HF_HUB_DISABLE_XET"] = "1"

# Setup cache NLTK
nltk_cache = os.path.join(root, ".cache", "nltk_data")
nltk.data.path.append(nltk_cache)
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab', download_dir=nltk_cache)

# Setup EasyNMT
smallmodel = 'opus-mt'
medio_model = 'mbart50_en2m'
bigmodel = 'm2m_100_1.2B'
model = EasyNMT(f'{bigmodel}', cache_folder=os.path.join(root, ".cache", "easynmt"), resume=True)


def f_flux2():
    global path_image_ref, path_image_ref2, combo_lora, combo_risoluzione, text, steps, canvas2, canvas3
    
    raw_text = text.get('1.0', tk.END).strip()
    print("Ripristino con Flux 2")
    print(f"Path riferimento 1: {path_image_ref}")
    print(f"Path riferimento 2: {path_image_ref2}")
    print(f"LoRA: {combo_lora.get()}")
    print(f"Risoluzione: {combo_risoluzione.get()}")
    print(f"Testo: {raw_text}")
    print(f"Steps: {steps.get()}")

    device = "cuda"
    dtype = torch.bfloat16

    # Caricamento pipeline
    pipe = Flux2KleinPipeline.from_pretrained("black-forest-labs/FLUX.2-klein-9B", torch_dtype=dtype)
    
    # Caricamento LoRA
    lora_name = combo_lora.get()
    if not lora_name.endswith('.safetensors'):
        lora_name += '.safetensors'
    path_lora = os.path.join(".", "lora_upscale", lora_name)
    
    pipe.load_lora_weights(path_lora, adapter_name='lora1')
    pipe.set_adapters('lora1', adapter_weights=0.8)
    
    print("Quantizzazione Transformer e Text Encoder")
    quantize(pipe.transformer, weights=qfloat8)
    freeze(pipe.transformer)
    quantize(pipe.text_encoder, weights=qfloat8)
    freeze(pipe.text_encoder)
    
    pipe.enable_model_cpu_offload()

    # Caricamento immagini PIL per l'infezenza
    images = []
    if path_image_ref and os.path.exists(path_image_ref):
        img1 = Image.open(path_image_ref).convert("RGB")
        images.append(img1)
    if path_image_ref2 and os.path.exists(path_image_ref2):
        img2 = Image.open(path_image_ref2).convert("RGB")
        images.append(img2)
    
    # Traduzione del prompt
    prompt_eng = None
    count = 0
    while prompt_eng is None and count < 10:
        try:
            prompt_eng = GoogleTranslator(source='it', target='en').translate(raw_text)
        except Exception as e:
            print(f"Traduzione Google fallita (tentativo {count + 1}): {e}")
        count += 1
    
    # Fallback su EasyNMT se Google Translator fallisce
    if prompt_eng is None:
        try:
            prompt_eng = model.translate(raw_text, source_lang='it', target_lang='en')
        except Exception as e:
            print(f"Traduzione EasyNMT fallita: {e}")
            prompt_eng = raw_text  # Fallback definitivo sul testo originale

    # Calcolo dimensioni output
    max_res = int(combo_risoluzione.get().replace('Ris:', '').strip()) 
    
    if images:
        w, h = images[0].size
        if w >= h:
            rw = max_res
            rh = (max_res * h) // w
        else:
            rh = max_res
            rw = (max_res * w) // h
    else:
        rw, rh = max_res, max_res

    # Gestione argomento image
    input_image = images[0] if len(images) == 1 else (images if len(images) > 1 else None)

    image = pipe(
        prompt=prompt_eng,
        image=input_image,
        height=rh,
        width=rw,
        guidance_scale=1.0,
        num_inference_steps=int(steps.get()),
        generator=torch.Generator(device=device).manual_seed(0)
    ).images[0]
    dirup = "./Upscale"
    os.makedirs(dirup, exist_ok=True)
    # Correzione: "spit" -> "split"
    base_name = os.path.splitext(os.path.basename(path_image_ref))[0]
    path_outup = f"{dirup}/Upscale_{base_name}.png"
    j = 1
    while os.path.exists(path_outup):
        path_outup = f"{dirup}/Upscale_{base_name}_{j}.png"
        j += 1

    image.save(path_outup)


frame_flux = tk.Frame(frame_frame, bg='light green')
frame_flux.grid(row=2, column=0)

button_ristora = tk.Button(frame_flux, text='Flux 2 9B\nRistora Immagine', bg='orange',command=f_flux2)
button_ristora.grid(row=0, column=0, sticky='nw')  # corretto `sticky`

steps = tk.Scale(frame_flux, from_=0, to=100, orient=HORIZONTAL)
steps.grid(row=0, column=1, sticky='nw')  # corretto `sticky`
steps.set(8)

lab = tk.Label(frame_flux, text='Lora Upscale')
lab.grid(row=0, column=2)

combo_lora = ttk.Combobox(frame_flux)
combo_lora.grid(row=0, column=3)
combo_lora.set('nolora')

def load_lora(event=None):
    models = []
    lora_dir = 'lora_upscale'
    if os.path.exists(lora_dir) and os.path.isdir(lora_dir):
        models = [os.path.basename(m) for m in os.listdir(lora_dir)]
    combo_lora['values'] = ['nolora'] + models
    combo_lora.update_idletasks()

# Carica valori una prima volta all'avvio
load_lora()
combo_lora.bind('<Button-1>', load_lora)

text = tk.Text(frame_flux, width=40, height=4)
text.grid(row=1, column=0, sticky='nw', padx=10, pady=10)

def f_select_lora(event=None):
    global combo_lora, text
    selected = combo_lora.get()

    if '(FK)r12_s700' in selected:
        # link lora: https://civitai.com/models/2859218/detail-reconstruction-upscaler-workflowklein-9b-turbo?modelVersionId=3229615
        # Trigger words ufficiali dell'autore: LoRA per ritratti/moda femminile,
        # ricostruisce dettagli reali su pelle, capelli e tessuti senza ridisegnare troppo il soggetto.
        prompt = "zqvx, sharpen the image, enrich the original textures with more detail."

    elif 'Flux2-Klein-Image-RestoreV1' in selected:
        # link: https://civitai.com/models/2474084/ultimate-upscaler-klein-9b?modelVersionId=2781657
        # Prompt esatto consigliato dall'autore per il miglior risultato (rimozione artefatti JPEG, blur, ecc.)
        prompt = ("restore the image quality, remove any compression artefacts, "
                  "remove any haze and soft edges, enrich the original with new intricate "
                  "detail in all textures and surfaces createing a professional photorealistic "
                  "photograph with natral lighting and skin texture.")

    elif 'flux2KLEIN9BE4BA9AE6B4B2E4BABAE5838FE4.Jk2G' in selected:
        # link: https://civitai.com/models/2804720/asian-portrait-realism-limb-restoration-flux2-klein-9b-lora?modelVersionId=3162365
        # Nessuna trigger word (l'autore lo dichiara esplicitamente: "无触发词").
        # L'effetto stilistico (tratti asiatici, pelle più chiara, corpo più snello,
        # correzione arti, sfondo sfocato) è applicato automaticamente dalla LoRA,
        # quindi basta un prompt generico di restauro/upscale, non serve descrivere il soggetto.
        prompt = ("ingrandisci e migliora l'immagine, ritratto fotorealistico, "
                "pelle naturale, dettagli nitidi, sfondo leggermente sfocato")
    else:
        prompt = "Ingrandisci e Migliora immagine"

    text.delete('1.0', tk.END)
    text.insert('1.0', prompt)
    return prompt

# Aggiorna il prompt ogni volta che si sceglie una LoRA diversa dalla combobox
combo_lora.bind('<<ComboboxSelected>>', f_select_lora)

# Popola il prompt di default all'avvio (nolora)
f_select_lora()

def f_ris():
    ris=1000
    risoluzioni=[]
    for j in range(1,30):
        risoluzioni.append(f'Ris:{ris}')
        ris=ris+100
    combo_risoluzione['values']=risoluzioni
combo_risoluzione = ttk.Combobox(frame_flux,values=[])
combo_risoluzione.grid(row=0, column=4)
f_ris()
combo_risoluzione.bind('<<Button-1>>',f_ris)
combo_risoluzione.set('Ris:1600')


window.mainloop()