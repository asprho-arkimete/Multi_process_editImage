
prompt="""
spread_legs_beta1, ragazza fotorealistica di 28 anni, stesso volto del riferimento, completamente nuda, 
distesa supina su:(un divano marrone/rosso di pelle del image di riferimento 2) , lei ha le gambe estremamente divaricate e sollevate in aria, ginocchia piegate, piedi visibili in telecamera,mani che tirano i glutei per aprire al massimo,
seno naturale morbido, capezzoli realistici, leggera peluria pubica brunetta,(figa estremamente dilatata),(grandi labbra della vagina estremamente dilatate),
(piccole labbra della vagina estremamente dilatate),vulva aperta e bagnata,canale vaginale aperto con interno visibile,clitoride visibile, 
ano estremamente dilatato, enorme apertura anale rilassata, bordo anale stirato al massimo, profondità rettale visibile, 
pelle iperrealistica con texture dettagliata, lucida di succhi, foto raw 8k, qualità massima, dettaglio anatomico estremo, realismo fotografico crudo
Mantieni sempre massima coerenza del soggetto nel image 1, del viso, della capigliatura nera, degli occhi neri e del fisico."""

token='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'

import os
os.environ["HF_TOKEN"] = token
# Cartella dove si trova lo script
import os
root = os.path.dirname(os.path.abspath(__file__))

os.environ["HF_HUB_DISABLE_XET"] = "1"
os.environ["HF_HOME"] = os.path.join(root, ".cache", "huggingface")
os.environ["TRANSFORMERS_CACHE"] = os.path.join(root, ".cache", "huggingface")

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
model = EasyNMT(f'{bigmodel}', cache_folder=os.path.join(root, ".cache", "easynmt"),resume=True)

trad = model.translate(prompt, source_lang='it', target_lang='en')
print(f"traduzione {trad}")