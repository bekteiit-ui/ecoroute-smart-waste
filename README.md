# EcoRoute: Belediyeler İçin Akıllı Atık Toplama ve Dinamik Rota Optimizasyonu

**Ders:** Programlama II  
**Proje Ekibi:**
* **Bekteiit** – Proje Lideri, Backend Mimarisi ve Rota Optimizasyon Motoru
* **Hasan** – Veritabanı Yönetimi (MS SQL), IoT Sensör Simülasyonu ve API Geliştirme
* **Arman** – Frontend Geliştirme, Canlı Harita Entegrasyonu ve Veri Görselleştirme

---

## 1. Projenin Amacı ve Hedef Kitlesi

### 1.1. Problemin Tanımı
Belediyelerin mevcut katı atık toplama operasyonları çoğunlukla **statik (sabit) çizelgelere** ve sürücülerin kişisel deneyimlerine dayanmaktadır. Bu geleneksel yaklaşım kamu kurumlarında üç temel soruna yol açmaktadır:
1. **Kaynak İsrafı:** Henüz dolmamış ($\%20 - \%30$ doluluk oranındaki) çöp konteynerlerine gereksiz araç gönderilmesi nedeniyle yüksek yakıt tüketimi, araç yıpranması ve personel mesai maliyeti oluşmaktadır.
2. **Çevre ve Halk Sağlığı Sorunları:** Beklenenden hızlı dolan konteynerlerin zamanında boşaltılamaması taşmalara, kötü kokuya, görüntü kirliliğine ve halk sağlığı risklerine neden olmaktadır.
3. **Trafik ve Operasyonel Körlük:** Ani trafik sıkışıklıkları, yol çalışmaları veya olumsuz hava koşulları karşısında sahadaki araçlara anlık müdahale edilememektedir.

### 1.2. Projenin Amacı
**EcoRoute**, klasik bir veri kayıt veya otomasyon yazılımı olmanın ötesine geçerek, belediyelerin atık toplama süreçlerini **gerçek zamanlı sensör verileri ve yapay zeka destekli rota optimizasyonu** ile yöneten bir karar destek ve operasyon platformudur. Sistem; yalnızca doluluk eşiği ($\%80$ ve üzeri) aşılan konteynerleri hedef alarak en kısa, en az yakıt tüketen ve trafik yoğunluğundan kaçınan dinamik rotalar üretir.

### 1.3. Hedef Kitle
* **Belediye Yöneticileri ve Filo Operatörleri:** Araç filosu kullanım oranlarını, yakıt/mesafe tasarruflarını, karbon emisyonu ($CO_2$) azaltımını ve anlık saha durumunu tek bir merkezi panelden (Dashboard) takip eden karar vericiler.
* **Temizlik İşleri Saha Personeli ve Sürücüler:** Kendilerine atanan dinamik rotaları, sıradaki durağı ve tahmini varış sürelerini (ETA) anlık bildirimlerle takip eden operatörler.
* **Vatandaşlar:** Taşmayan, temiz konteynerler sayesinde daha sağlıklı bir kent yaşamına kavuşan ve belediye bütçesinin verimli kullanılmasından doğrudan fayda sağlayan ilçe/şehir sakinleri.

---

## 2. Sistem Özellikleri ve Arayüz Tasarımı (Dashboard)

EcoRoute kullanıcı arayüzü, operatörlerin tüm şehri tek ekrandan yönetebileceği modern, veri odaklı bir kontrol merkezi olarak tasarlanmıştır:

* **Üst Özet Kartları (KPI Göstergeleri):** Toplam konteyner sayısı, $\%80$ üzeri doluluğa ulaşan acil konteynerler, aktif araç sayısı, optimize edilen rota adedi, günlük tasarruf edilen mesafe ($\text{km}$), yakıt ($\text{L}$) ve tamamlanan toplama sayısı.
* **Canlı Harita ve Rota İzleme (Route Overview):** Şehir haritası üzerinde ana depo (Depot), tamamlanan, devam eden, geciken ve bekleyen durakların renk kodlarıyla gösterimi; toplama araçlarının harita üzerindeki canlı konum takibi.
* **Canlı Araç Takip Paneli (Live Vehicle Tracking):** Her bir aracın (örn. `VH-102`) rota ilerleme yüzdesi, sıradaki durağı, tahmini varış süresi (ETA) ve gecikme durumları.
* **Yapay Zeka Karar Destek Önerileri (Next Best Action & Insights):** Trafik sıkışıklığı veya araç arızası durumunda sistemin sunduğu tek tıkla uygulanabilir aksiyon önerileri (örn. *"Geciken VH-104 aracının rotasını VH-103 aracına devret"*).
* **Analitik ve Sürdürülebilirlik Grafikleri:** Haftalık rota verimlilik trendi, planlanan ve gerçekleşen toplama karşılaştırmaları, araç kullanım dağılımı (aktif, beklemede, bakımda) ve $CO_2$ emisyon azaltım metrikleri.

---

## 3. Kullanılan Teknolojiler ve Mimari Yapı

### 3.1. Teknoloji Yığını (Tech Stack)

| Katman | Teknoloji / Araç | Kullanım Amacı |
| :--- | :--- | :--- |
| **Backend (Zorunlu)** | **Python 3.11+ & FastAPI** | Yüksek performanslı, asenkron RESTful API servisleri ve otomatik Swagger/OpenAPI dokümantasyonu. |
| **Optimizasyon Motoru** | **Google OR-Tools (CVRP)** | Kapasite Kısıtlı Araç Rotalama Problemi (CVRP) çözümü ve dinamik rota hesaplama. |
| **Veritabanı** | **Microsoft SQL Server (MS SQL)** | İlişkisel veri depolama (Araçlar, Konteynerler, Sensör Logları, Rotalar, Kullanıcılar). |
| **ORM & Bağlantı** | **SQLAlchemy & pyodbc** | Python ile MS SQL Server arasında güvenli veri erişimi ve şema yönetimi. |
| **Frontend (Arayüz)** | **HTML5, Tailwind CSS, JavaScript (React)** | Referans dashboard tasarımına uygun modern ve duyarlı (responsive) web arayüzü. |
| **Harita & Grafik** | **Leaflet.js / OSRM & Chart.js** | İnteraktif şehir haritası, renkli rota çizimleri ve gerçek zamanlı analitik grafikler. |
| **Sürüm Kontrolü** | **Git & GitHub** | Ekip içi kod paylaşımı, branch yönetimi ve kod inceleme (Pull Request) süreçleri. |

### 3.2. Sistem Mimarisi (Veri Akışı)

```text
+-------------------------------------------------------------------+
|                  FRONTEND (Web Dashboard - Arman)                 |
|  [KPI Kartları]   [Canlı Harita (Leaflet)]   [Analitik & AI Panel] |
+---------------------------------+---------------------------------+
                                  | HTTP / REST API (JSON)
                                  v
+-------------------------------------------------------------------+
|               BACKEND API KATMANI (FastAPI - Bekteiit)            |
|  /api/bins   /api/vehicles   /api/routes/optimize   /api/analytics|
+----------------+---------------------------------+----------------+
                 |                                 |
                 v                                 v
+---------------------------------+   +-----------------------------+
|   ROTA OPTİMİZASYON MOTORU      |   |   VERİTABANI KATMANI        |
|   (Google OR-Tools / Heuristic) |   |   (MS SQL Server - Hasan)   |
| - Doluluk Eşiği Filtresi (>%80) |   | - Konteyner & Sensör Tablosu|
| - Araç Kapasite & Trafik Analizi|   | - Araç Filosu & Rota Logları|
+---------------------------------+   +--------------+--------------+
                                                     ^
                                                     | Periyodik Veri
                                      +--------------+--------------+
                                      |   IoT SENSÖR SİMÜLATÖRÜ     |
                                      |   (Python Arka Plan Servisi)|
                                      +-----------------------------+
```

### 3.3. Veritabanı Tasarımı (MS SQL Server Temel Tabloları)
* `Containers`: `container_id`, `latitude`, `longitude`, `zone_name`, `capacity_liters`, `current_fill_rate`, `last_updated`
* `Vehicles`: `vehicle_id`, `plate_number`, `driver_name`, `max_capacity_kg`, `status` (On Route, Idle, Maintenance), `current_lat`, `current_lng`
* `Routes`: `route_id`, `vehicle_id`, `created_at`, `total_distance_km`, `estimated_fuel_l`, `status` (Completed, In Progress, Delayed)
* `RouteStops`: `stop_id`, `route_id`, `container_id`, `stop_order`, `eta_minutes`, `is_collected`
* `OptimizationLogs`: `log_id`, `route_id`, `distance_saved_km`, `fuel_saved_l`, `co2_reduced_kg`

---

## 4. Geliştirme Sürecinde Kullanılan MCP Sunucuları ve Skill'ler

Proje geliştirme sürecinde yapay zeka ajanlarından (Claude / Gemini / Cursor) maksimum verim almak ve standartlara uygun kod üretmek amacıyla aşağıdaki **Model Context Protocol (MCP)** sunucuları ve **Skill (Yetenek/Otomasyon)** yapıları aktif olarak kullanılmıştır:

### 4.1. Kullanılan MCP Sunucuları
1. **`mssql-mcp` (Veritabanı MCP Sunucusu):**
   * **Kullanım Amacı:** MS SQL Server veritabanı şemasının oluşturulması, tablo ilişkilerinin (Foreign Key) doğrulanması ve karmaşık analitik sorguların (günlük yakıt/mesafe tasarrufu hesaplamaları) test edilerek optimize edilmesi için kullanılmıştır.
2. **`github-mcp` (Sürüm Kontrol ve İş Birliği MCP Sunucusu):**
   * **Kullanım Amacı:** Ekip üyelerinin açtığı Pull Request'lerin (PR) otomatik incelenmesi, commit mesajlarının standartlaştırılması ve Jira görevleriyle eşleşen branch yapısının yönetilmesi amacıyla kullanılmıştır.
3. **`atlassian-jira-mcp` (Proje Yönetimi MCP Sunucusu):**
   * **Kullanım Amacı:** Proje lideri Bekteiit tarafından sprint planlamalarının oluşturulması, kullanıcı hikayelerinin (User Stories) teknik alt görevlere bölünmesi ve haftalık ilerleme raporlarının çıkarılması için kullanılmıştır.
4. **`context7` / `fetch-mcp` (Güncel Dokümantasyon MCP Sunucusu):**
   * **Kullanım Amacı:** FastAPI asenkron veritabanı bağlantıları (`pyodbc`), Google OR-Tools CVRP parametreleri ve Leaflet.js rota katmanlarının güncel dokümantasyonlarına geliştirme ortamından çıkmadan erişmek için kullanılmıştır.

### 4.2. Geliştirilen ve Kullanılan AI Skill Yapıları
1. **`fastapi-endpoint-architect` Skill:**
   * **Amacı:** Pydantic doğrulama şemaları (Request/Response models), HTTP hata yönetimi (`HTTPException`) ve MS SQL oturum yönetimini içeren standart FastAPI uç noktalarını hatasız bir şekilde oluşturmak.
2. **`vrp-route-optimizer` Skill:**
   * **Amacı:** Konteyner koordinatları arasındaki mesafe matrisini hesaplayan, $\%80$ doluluk eşiğini filtreleyen ve araç kapasitelerine göre en kısa rotayı üreten algoritma şablonlarını yapılandırmak.
3. **`iot-telemetry-generator` Skill:**
   * **Amacı:** Sahadaki gerçek sensörlerin davranışını taklit eden (bölge yoğunluğuna ve günün saatine göre doluluk artışı üreten) gerçekçi test verileri oluşturmak.

---

## 5. Görev Dağılımı ve Süreç Yönetimi

Proje yönetimi **Jira** üzerinden Agile/Scrum metodolojisine uygun olarak yürütülmekte, kod geliştirme süreçleri ise **GitHub** üzerinde `main`, `develop` ve kişiye özel `feature/*` dalları (branches) ile kontrol edilmektedir.

### 5.1. Ekip İçi Rol ve Sorumluluklar

| Ekip Üyesi | Rol | Temel Sorumluluklar |
| :--- | :--- | :--- |
| **Bekteiit** | **Proje Lideri & Backend / Algoritma Geliştirici** | • Jira panosunun kurulumu, sprintlerin açılması ve görev dağılımı takibi.<br>• GitHub depo yönetimi ve PR onay süreçleri.<br>• FastAPI temel mimarisi ve Google OR-Tools rota optimizasyon motorunun kodlanması. |
| **Hasan** | **Veritabanı Mimarı & IoT / API Geliştirici** | • MS SQL Server veritabanı tablolarının ve ilişkilerinin tasarlanması.<br>• IoT konteyner doluluk sensörü simülatörünün geliştirilmesi.<br>• Araç takip, uyarı (Alerts) ve analitik hesaplama API uç noktalarının yazılması. |
| **Arman** | **Frontend Geliştirici & UI/UX Tasarımcısı** | • Referans tasarıma uygun modern kontrol paneli (Dashboard) arayüzünün kodlanması.<br>• Canlı harita üzerinde renkli rota çizimleri ve hareketli araç ikonlarının entegrasyonu.<br>• KPI kartları, trend grafikleri ve yapay zeka öneri kartlarının geliştirilmesi. |

### 5.2. Sprint Zaman Planlaması

* **Sprint 1 (Hafta 1-2) – Analiz, Tasarım ve Altyapı:** Gereksinim analizi, Jira/GitHub kurulumu, MS SQL Server veritabanı şemasının oluşturulması ve FastAPI proje iskeletinin ayağa kaldırılması.
* **Sprint 2 (Hafta 3-4) – Çekirdek Backend ve Rota Motoru (Ara Sunum Hedefi):** IoT sensör simülatörünün tamamlanması, temel CRUD API'lerinin yazılması, rota optimizasyon algoritmasının ilk prototipinin çalıştırılması ve **Ara Sunum** gerçekleştirilmesi.
* **Sprint 3 (Hafta 5-6) – Dashboard Arayüzü ve Harita Entegrasyonu:** Web arayüzünün geliştirilmesi, canlı harita üzerinde rota görselleştirme, araç takip paneli ve "Next Best Action" öneri modülünün bağlanması.
* **Sprint 4 (Hafta 7-8) – Test, Optimizasyon ve Final Sunumu:** Uçtan uca sistem testleri, performans iyileştirmeleri, maliyet/kazanç analizlerinin doğrulanması ve **Final Sunumu**.

---

## 6. Maliyet Hesabı ve Kazanç Modeli

### 6.1. Tahmini Maliyet Hesabı (Orta Ölçekli Bir İlçe Belediyesi İçin)
Ortalama $500$ akıllı konteyner ve $15$ atık toplama aracına sahip bir belediye senaryosu baz alınmıştır:

| Gider Kalemi | Açıklama | Aylık Tahmini Maliyet | Yıllık Tahmini Maliyet |
| :--- | :--- | :--- | :--- |
| **Bulut Sunucu (Backend & Engine)** | 4 vCPU, 8 GB RAM Bulut Sunucu (AWS EC2 / Azure App Service) | $\$45$ | $\$540$ |
| **Veritabanı Barındırma** | Yönetilen MS SQL Server / Azure SQL Database | $\$60$ | $\$720$ |
| **Harita ve Yönlendirme API'leri** | Self-hosted OSRM (OpenStreetMap) + Yedek Trafik API kotası | $\$25$ | $\$300$ |
| **Bakım, İzleme ve Loglama** | Sistem izleme, yedekleme ve güvenlik sertifikaları | $\$20$ | $\$240$ |
| **Toplam İşletme Gideri** | **Sunucu, Veritabanı ve API Giderleri Toplamı** | **$\$150$** | **$\$1.800$** |

*(Not: Geliştirme aşamasında öğrenciler ve yerel test ortamı için açık kaynaklı araçlar ve ücretsiz bulut kredileri kullanıldığından başlangıç yazılım geliştirme maliyeti minimum düzeydedir.)*

### 6.2. Kazanç Modeli (İş Modeli)
EcoRoute, kamu kurumlarına (B2G - Business to Government) yönelik sürdürülebilir ve ölçeklenebilir üç katmanlı bir gelir modeline sahiptir:

1. **SaaS Abonelik Modeli (Araç ve Konteyner Başına Lisanslama):**
   * **Başlangıç Paketi (Küçük Belediyeler - 10 Araca Kadar):** Aylık $\$600$ (Yıllık $\$7.200$).
   * **Profesyonel Paket (İlçe Belediyeleri - 10-30 Araç):** Aylık $\$1.250$ (Yıllık $\$15.000$).
   * **Kurumsal Paket (Büyükşehir Belediyeleri - 30+ Araç & Özel Entegrasyon):** Yıllık $\$35.000+$.
2. **Tasarruf Paylaşımı (Performans Odaklı Sözleşme):**
   * Belediyenin ilk 6 aydaki yakıt ve bakım giderleri baz alınarak, sistemin sağladığı net yakıt tasarrufunun $\%20$'si oranında başarı primi (Success Fee) alınması.
3. **IoT Donanım Entegrasyon ve Kurulum Danışmanlığı:**
   * Halihazırda sensörü bulunmayan belediyelere ultrasonik doluluk sensörü tedariki ve sisteme entegrasyonu üzerinden tek seferlik kurulum geliri.

### 6.3. Yatırım Getirisi (ROI) ve Belediye Tasarruf Analizi
$15$ araçlık bir belediye filosunda her aracın günde ortalama $120\text{ km}$ yol yaptığı ve $100\text{ km}$'de $35\text{ L}$ motorin tükettiği varsayıldığında:

$$\text{Günlük Toplam Yakıt Tüketimi} = 15 \times \frac{120}{100} \times 35 = 630\text{ L/gün}$$

EcoRoute optimizasyonu ile rotalarda sağlanan ortalama $\%18$ mesafe ve yakıt tasarrufu sonucunda:

$$\text{Günlük Yakıt Tasarrufu} = 630 \times 0.18 = 113.4\text{ L/gün} \approx 3.402\text{ L/ay}$$

Motorin litre fiyatının ortalama $\$1.25$ olduğu senaryoda belediyenin **aylık brüt yakıt tasarrufu**:

$$3.402\text{ L} \times \$1.25 = \$4.252,50\text{/ay}$$

Belediye, aylık $\$1.250$ yazılım lisans bedeli ödediğinde dahi **net aylık $\$3.002,50$ (yıllık $\$36.030$) kâr** elde etmekte; aynı zamanda yıllık yaklaşık $98\text{ ton}$ daha az $CO_2$ salınımı gerçekleştirerek çevresel sürdürülebilirlik hedeflerine ulaşmaktadır.