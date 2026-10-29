import io, os, re, json, time, zipfile, base64
from PIL import Image
from docx import Document
import streamlit as st

st.set_page_config(page_title='Görsel Stüdyom', page_icon='🎬', layout='wide')
st.title('🎬 Görsel Stüdyom')
st.caption('İyiler Ölmez ve Gazali için senaryodan sıralı, bağımsız görseller')

CHANNEL_STYLE = {
 'İyiler Ölmez': ('historical cinematic realistic painterly illustration, ancient Middle Eastern historical setting, modest authentic historical clothing, grounded sandstone architecture, rich layered environmental storytelling, evocative warm lighting, consistent sophisticated color grading. Any prophet must be shown exclusively from behind at distance; never reveal his face, no facial details, no halos that resemble portraits. Respectful religious visual treatment.', 'Olayların geçtiği yerleri ve karakterlerin eylemlerini göster. Peygamber yüzünü kesinlikle gösterme.'),
 'Gazali': ('cinematic sophisticated realistic painterly illustration, medieval Islamic scholarly world, historic libraries, manuscripts, stone madrasas, restrained symbolism, luminous dramatic atmosphere, contemplative emotional tone, rich composition, recurring consistent scholarly character. No modern objects.', 'Hikmet, tefekkür, anlatılan kıssa ve güçlü metaforları görselleştir.'),
}


def get_text(file, typed):
 if not file: return typed.strip()
 if file.name.lower().endswith('.docx'):
  return '\n'.join(p.text for p in Document(io.BytesIO(file.getvalue())).paragraphs if p.text.strip()).strip()
 return file.getvalue().decode('utf-8-sig',errors='replace').strip()

def offline_scenes(txt):
 # Approximate, fully offline preview. Production planning uses Gemini when available.
 sentences = [s.strip() for s in re.split(r'(?<=[.!?…])\s+(?=[A-ZÇĞİÖŞÜ“])',txt.replace('\r',' ')) if s.strip()]
 if not sentences: sentences = [txt]
 chunks=[]; current=''
 for s in sentences:
  if len(current)+len(s)>250 and current:
   chunks.append(current); current=''
  current=(current+' '+s).strip()
 if current: chunks.append(current)
 # no artificial inflation; separate genuine narrative beats only
 return [{'id':i+1,'title':f'Sahne {i+1:03}', 'excerpt':c, 'visual':c} for i,c in enumerate(chunks)]

def plan_with_gemini(txt, channel, key):
 from google import genai
 from google.genai import types
 cli=genai.Client(api_key=key)
 instruction=f'''You are the storyboard director for a Turkish YouTube narration channel: {channel}. Return a strict JSON object with key "scenes" array. Analyze the ENTIRE provided script; create visual shots in exact narrative order. Determine the number of images from real visual changes; avoid redundant shots. For a short 100-250 word intro aim 8-16 unique scenes; for a full 25-minute script decide as needed. Each scene: title (short Turkish), excerpt (verbatim short Turkish excerpt from script), visual (visually precise English description of ONE shot, with setting, actors, action, framing, light, period details). Do not invent events not in the script. Do not include on-screen text, captions or collage. {CHANNEL_STYLE[channel][1]} Return only valid JSON. Script:\n{txt[:60000]}'''
 resp=cli.models.generate_content(model='gemini-2.5-flash',contents=instruction,config=types.GenerateContentConfig(response_mime_type='application/json'))
 obj=json.loads(resp.text)
 return [dict(id=i+1,title=str(x.get('title','Sahne')),excerpt=str(x.get('excerpt','')),visual=str(x.get('visual',''))) for i,x in enumerate(obj['scenes'])]

def readable_error(e, engine):
 msg=str(e)
 lower=msg.lower()
 if 'api_key_invalid' in lower or 'api key not valid' in lower or 'incorrect api key' in lower:
  return f'Geçersiz API anahtarı. Seçili servis: {engine}. Google anahtarı ile OpenAI anahtarı birbirinin yerine kullanılamaz. Ayrıntı: {msg[:700]}'
 if 'insufficient_quota' in lower or 'billing' in lower or 'quota' in lower:
  return f'API bakiyesi, kota veya faturalandırma sorunu. Ayrıntı: {msg[:700]}'
 if 'model_not_found' in lower or 'does not exist' in lower:
  return f'Model hesabında kullanılabilir değil. Ayrıntı: {msg[:700]}'
 return f'{type(e).__name__}: {msg[:800]}'

def plan_with_openai(txt, channel, key):
 from openai import OpenAI
 client=OpenAI(api_key=key)
 instruction=f"""Türkçe YouTube anlatısının yönetmenisin. Kanal: {channel}. Bütün metni sırayla incele. Gerçek görsel değişimlerine göre bağımsız sahneler oluştur, tekrardan kaçın. Her sahnede title kısa Türkçe başlık, excerpt metinden kısa birebir alıntı, visual ise İngilizce ayrıntılı, tek karelik kompozisyon olsun. Asla metinde olmayan olay ekleme. Ekranda yazı veya kolaj olmasın. {CHANNEL_STYLE[channel][1]}. Kesin JSON döndür, tek anahtar scenes olsun. Metin: {txt[:60000]}"""
 response=client.chat.completions.create(model='gpt-4.1-mini',response_format={'type':'json_object'},messages=[{'role':'user','content':instruction}])
 obj=json.loads(response.choices[0].message.content)
 return [dict(id=i+1,title=str(x.get('title','Sahne')),excerpt=str(x.get('excerpt','')),visual=str(x.get('visual',''))) for i,x in enumerate(obj['scenes'])]

def generate_one(scene, channel, engine, key):
 base=CHANNEL_STYLE[channel][0]
 prompt=f'{scene["visual"]}\nSTYLE: {base}\nOne standalone distinct complete composition. Widescreen 16:9 landscape frame. No text, subtitles, watermark, logos, frame or panel borders.'
 if engine.startswith('Nano'):
  from google import genai
  from google.genai import types
  cli=genai.Client(api_key=key)
  res=cli.models.generate_content(model='gemini-2.5-flash-image',contents=prompt,config=types.GenerateContentConfig(response_modalities=['TEXT','IMAGE']))
  for candidate in res.candidates or []:
   for part in candidate.content.parts or []:
    if part.inline_data and part.inline_data.data:
     return Image.open(io.BytesIO(part.inline_data.data)).convert('RGB'),prompt
  raise RuntimeError('Google görsel döndürmedi; model erişimini ve bakiyeni kontrol et.')
 else:
  from openai import OpenAI
  result=OpenAI(api_key=key).images.generate(model='gpt-image-2.5-flare',prompt=prompt,size='1536x1024',n=1)
  return Image.open(io.BytesIO(base64.b64decode(result.data[0].b64_json))).convert('RGB'),prompt

def jpeg_bytes(im):
 # Fit rather than upscale using crops; standard final delivery 1920x1080
 from PIL import ImageOps
 im=ImageOps.fit(im,(1920,1080),method=Image.Resampling.LANCZOS,centering=(.5,.5))
 buf=io.BytesIO(); im.save(buf,format='JPEG',quality=93,optimize=True)
 return buf.getvalue()

def safe_name(s):
 s=s.translate(str.maketrans('çğıöşüÇĞİÖŞÜ','cgiosuCGIOSU'))
 return re.sub(r'[^a-zA-Z0-9]+','_',s).strip('_')[:45] or 'Sahne'

with st.sidebar:
 st.subheader('Proje ayarları')
 channel=st.selectbox('Kanal',list(CHANNEL_STYLE))
 engine=st.selectbox('Görsel motoru',['Nano Banana (Google)','ChatGPT Image (OpenAI)'])
 st.caption('Google AI Pro ve ChatGPT Plus abonelikleri API ücretlerini içermez.')
 key=st.text_input('API anahtarın',type='password',help='Sadece mevcut oturumda kullanılır; indirilen dosyalara yazılmaz.')
 st.warning('Anahtarını kimseyle paylaşma. API kullanımı ayrıca ücretli olabilir. Herkese açık uygulamada kişisel anahtar girmek yerine özel erişim kullanman daha güvenlidir.')
 st.caption('Nano Banana seçiliyse Google AI Studio anahtarı; ChatGPT Image seçiliyse OpenAI Platform anahtarı gerekir.')

file=st.file_uploader('Senaryo dosyası (.txt veya .docx)',type=['txt','docx'])
typed=st.text_area('Ya da senaryoyu buraya yapıştır',height=190,placeholder='Bir şehir düşünün...')
script=get_text(file,typed)
left,right=st.columns(2)
with left:
 if st.button('① Sahne planı oluştur',type='primary',use_container_width=True,disabled=not bool(script)):
  with st.spinner('Senaryoyu sahnelere ayırıyorum...'):
   try:
    if key and engine.startswith('Nano'):
     scenes=plan_with_gemini(script,channel,key); mode='Yapay zekâ analizi'
    elif key and engine.startswith('ChatGPT'):
     scenes=plan_with_openai(script,channel,key); mode='OpenAI sahne analizi'
    else:
     scenes=offline_scenes(script); mode='Ücretsiz taslak (otomatik bölme)'
    st.session_state['scenes']=scenes
    st.session_state['images']={}
    st.session_state['mode']=mode
    st.session_state['last_script']=script
    st.session_state['last_channel']=channel
   except Exception as e: st.error(f'Sahne planı oluşturulamadı: {e}')
with right:
 st.caption('Anahtar yoksa ücretsiz basit taslak; anahtar varsa seçtiğin servisle ayrıntılı sahne analizi yapılır.')

if 'scenes' in st.session_state:
 scenes=st.session_state['scenes']
 st.info(f'Plan: {len(scenes)} sahne · {st.session_state.get("mode", "Taslak")} · Üretim adımları kontrol sende.')
 st.caption('Sahne tanımlarını düzenleyebilirsin. Ayrı görseller üretilir; storyboard tek görsele sıkıştırılmaz.')
 for i, s in enumerate(scenes):
  with st.expander(f'{i+1:03} · {s["title"]}',expanded=i<2):
   s['title']=st.text_input('Sahne adı',value=s['title'],key=f't{i}')
   st.caption(s['excerpt'])
   s['visual']=st.text_area('Görsel tanımı / prompt',value=s['visual'],key=f'v{i}',height=90)
 maxshots=len(scenes)
 count=st.number_input('Bu sefer kaç sahne üretilsin?',min_value=1,max_value=maxshots,value=min(3,maxshots),step=1)
 st.caption('İlk denemede 1–3 sahne seçmeni öneririm; her görselin API maliyeti olabilir.')
 if st.session_state.get('last_errors'):
  st.error('Son üretim hataları (kalıcı):')
  for error in st.session_state['last_errors']:
   st.code(error)
 if st.button('② Görselleri üret',type='primary',disabled=not bool(key)):
  st.session_state['last_errors']=[]
  progress=st.progress(0)
  images=st.session_state.setdefault('images',{})
  for j,s in enumerate(scenes[:count]):
   if s['id'] in images:
    progress.progress((j+1)/count);continue
   try:
    with st.spinner(f'Üretiliyor: {s["id"]:03} {s["title"]}'):
     img,prompt=generate_one(s,channel,engine,key)
     images[s['id']]={'bytes':jpeg_bytes(img),'prompt':prompt}
   except Exception as e:
    st.session_state['last_errors'].append(f'{s["id"]:03}: '+readable_error(e,engine))
   progress.progress((j+1)/count)
  st.rerun()
 images=st.session_state.get('images',{})
 st.write(f'**Tamamlanan:** {len(images)} / {len(scenes)}')
 if images:
  cols=st.columns(3)
  for k, rec in sorted(images.items()):
   with cols[(k-1)%3]:
    st.image(rec['bytes'],caption=f'{k:03} · {scenes[k-1]["title"]}',use_container_width=True)
 data={'channel':channel,'engine':engine,'scenes':scenes}
 zip_buffer=io.BytesIO()
 with zipfile.ZipFile(zip_buffer,'w',zipfile.ZIP_DEFLATED) as z:
  z.writestr('SAHNE_PLANI.json',json.dumps(data,ensure_ascii=False,indent=2))
  z.writestr('SAHNE_LISTESI.csv','No;Sahne;Metin;Dosya\n'+'\n'.join(f'{s["id"]:03};{s["title"].replace(";",",")};{s["excerpt"].replace(";",",")};{s["id"]:03}_{safe_name(s["title"])}.jpg' for s in scenes))
  for s in scenes:
   z.writestr(f'PROMPTLAR/{s["id"]:03}_{safe_name(s["title"])}.txt',images.get(s['id'],{}).get('prompt',s['visual']))
   if s['id'] in images:
    z.writestr(f'GORSELLER/{s["id"]:03}_{safe_name(s["title"])}.jpg',images[s['id']]['bytes'])
 st.download_button('③ ZIP paketini indir',zip_buffer.getvalue(),file_name=f'{safe_name(channel)}_Gorsel_Paketi.zip',mime='application/zip',use_container_width=True)
 st.caption('ZIP içindeki GORSELLER klasöründe yalnızca gerçekten üretilmiş kareler bulunur; diğerleri prompt olarak saklanır.')
