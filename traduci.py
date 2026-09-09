from logging import exception
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

def traduci(text,org='ita',dest='eng'):
    model_name = "facebook/nllb-200-distilled-600M"  # versione leggera
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    tokenizer.src_lang = f"{org}_Latn"
    text = "una bella ragazza giovane"
    inputs = tokenizer(text, return_tensors="pt")

    translated = model.generate(
        **inputs,
        forced_bos_token_id=tokenizer.convert_tokens_to_ids(f"{dest}_Latn"),
        max_length=1000
    )
    result = tokenizer.batch_decode(translated, skip_special_tokens=True)[0]
    print(result)
    return result

from deep_translator import GoogleTranslator
text="""clothesonoffv2, Rimuovi completamente i vestiti, 
rimuovi il camice bianco, rimuovi la maglia blue, rimuovi i pantaloni blue, una ragazza totalmente nuda, seno piccolo nudo naturale, capezzoli dettagliati, 
visuale frontale del pube con pochi peli naturali,visuale frontale dettagli genitali femminili;
Mantieni sempre massima coerenza del soggetto nel image 1, del viso, capigliatura, occhi e fisico""".strip()
while True:
    try:
        translated = GoogleTranslator(source='it', target='en').translate(text=text)
        print(f"traduzione: {translated}")
        break
    except exception as error:
        print(f"errore: {error}")
        
    finally:
        print("traduzione ok")
