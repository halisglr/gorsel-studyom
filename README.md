# Görsel Stüdyom

İyiler Ölmez / Gazali için senaryodan sahne planı, bağımsız görsel üretimi ve numaralı ZIP çıktısı.

## Kullanma (internette yayınlamak)
1. GitHub hesabı açın. Yeni bir *public* repository açın.
2. Bu klasördeki `app.py` ve `requirements.txt` dosyalarını GitHub reposuna yükleyin (README isteğe bağlı).
3. https://share.streamlit.io adresinden GitHub ile giriş yapıp **Create app** seçin.
4. Repository ve ana dosya olarak `app.py` seçip **Deploy** deyin.
5. Uygulama URL'sini tarayıcıdan açın. Kanal seçin, senaryo yapıştırın, sahne planı oluşturun.
6. Gerçek görsel üretmek isterseniz Google AI Studio (https://aistudio.google.com/apikey) veya OpenAI (https://platform.openai.com/api-keys) API anahtarı edinin ve yan menüye girin.
7. İlk denemede 1-3 sahne üretin. Sonra ZIP'i indirin.

## Önemli
- Google AI Pro aboneliği Gemini API kullanımının dahil olduğu anlamına gelmez.
- ChatGPT Plus aboneliği OpenAI API kullanımını içermez.
- Bu uygulama Flow web sitesine bağlanmaz; doğrudan Google Gemini API'deki Nano Banana modelini kullanır.
- API çağrısı için internet ve uygun kota/faturalandırma gerekir.
- API anahtarlarını GitHub'a yüklemeyin; bu uygulamada yalnızca özel şifre alanına girin.
- Uygulama örnek sürümdür; gerçek API anahtarıyla uçtan uca üretim burada test edilmemiştir.
- Üretilen kareler 16:9 olacak şekilde 1920×1080 çıktı dosyasına sığdırılır. Kaynak çözünürlük daha düşükse bu gerçek ayrıntıyı artırmaz.
