---
name: fastapi-modul-uretimi
description: EcoRoute projesi için standart Pydantic şemalı FastAPI router ve endpoint üretimi yapar.
---
1. Tüm yeni endpoint'leri `app/routers/` altında modüler olarak oluştur.
2. İstek ve yanıt modellerini `app/schemas.py` içinde Pydantic `BaseModel` ile tanımla.
3. Her endpoint için Swagger (`/docs`) açıklaması ve HTTP hata yönetimi (`HTTPException`) ekle.
