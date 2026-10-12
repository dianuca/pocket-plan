# PocketPlan — instrucțiuni pentru agenți

## Proiect și scop

PocketPlan este o aplicație Django de buget personal, inspirată dintr-un Excel. Include venituri, cheltuieli, rate și rezumat lunar. Direcțiile următoare sunt graficele, economiile, fondul personal lunar și închiderea lunii cu raport PDF.

Citește `POCKETPLAN_ROADMAP.md` pentru priorități și criterii de acceptare. Verifică starea reală în cod: checklist-ul nu este dovadă că o funcție a fost testată sau terminată.

## Stack

- Python, Django 5.2, SQLite, Django Templates, HTML/CSS/JavaScript.
- Verifică versiunile exacte și configurația din repository înainte de lucru.
- Păstrează arhitectura existentă. Nu adăuga SPA, REST API, framework UI sau dependențe fără o cerință ori o necesitate explicată și convenită.
- Reutilizează formularele, serviciile, template-urile și stilurile existente.

## Mod de colaborare

- Diana învață Django. Comunică în română, simplu, și explică schimbările relevante.
- Lucrează la un singur obiectiv și în pași mici. Un roadmap nu autorizează implementarea tuturor etapelor.
- Când cererea este de implementare, poți edita fișierele și rula verificările necesare fără confirmări repetate pentru fiecare pas.
- Când cererea este doar de analiză sau explicație, nu modifica fișierele.
- Pentru buguri, reproduce problema sau precizează ce dovezi lipsesc. Nu prezenta o ipoteză ca diagnostic confirmat.
- Dacă lipsește o decizie care schimbă regulile de business, cere clarificare și continuă lucrul independent care nu depinde de ea.
- La final, spune ce s-a schimbat, de ce, ce ai verificat și ce rămâne de verificat manual.

## GitFlow

- `main`: versiuni stabile; `develop`: integrare.
- Funcționalități pe `feature/<nume>`; corecții pe `fix/<nume>`.
- Înainte de editări, verifică ramura curentă și `git status`.
- Dacă ramura curentă corespunde cererii, continuă pe ea. Creează o ramură nouă din develop actualizat când obiectivul cere asta și starea de lucru permite.
- Nu suprascrie, șterge, reseta sau ascunde modificările utilizatoarei pentru a schimba ramura.
- Nu face commit, push, merge, publicare sau deploy fără instrucțiune explicită. O cerere pentru commit nu autorizează automat push sau merge.
- Nu modifica istoricul Git și nu face force push fără cerere explicită.
- Explică pașii Git din interfața VS Code când Diana îi execută; comenzile terminalului sunt potrivite pentru Django și verificări.

## Reguli de date și acces

- Limitează fiecare lookup, listă și agregare la utilizatorul autentificat.
- Stabilește `owner` pe server; nu îl accepta din formularul POST.
- Folosește `Decimal` pentru calculele financiare; nu calcula sume cu float în backend.
- Validează sumele și datele în formulare/servicii. Nu presupune că `model.save()` execută validarea modelului.
- Păstrează CSRF și folosește POST pentru operațiile de modificare, ștergere și închidere a lunii.
- Respectă filtrul lunii și tratează explicit lunile fără date.
- Economiile sunt sold inițial plus depuneri minus retrageri. Definește separat efectul transferurilor asupra bugetului lunar pentru a evita dubla numărare.
- Fondul personal este o alocare, nu o cheltuială. Cheltuiala din fond intră o singură dată în total.
- Ratele se includ doar în lunile active, conform serviciilor existente. Numărul de rate rămase este calcul calendaristic, nu confirmare de plată.
- La implementarea închiderii lunii, rapoartele trebuie să fie snapshot-uri independente de modificările ulterioare ale datelor.
- Blocarea unei luni se aplică în backend, inclusiv când datele sunt mutate între luni prin editare.

## Interfață

- Păstrează aspectul modern existent: sidebar închis la culoare, fundal deschis, accent violet și carduri rotunjite.
- Reutilizează selectorul de lună/an pe toate paginile relevante.
- Modalele păstrează valorile introduse și afișează erorile de validare. Anularea nu salvează și nu șterge date.
- Păstrează blurul convenit asupra conținutului, cu sidebar clar pe desktop.
- Evită formularele imbricate și ID-urile duplicate în aceeași pagină, inclusiv între formularul de adăugare și cel încărcat în modal; folosește prefixe de formular când este necesar.
- Menține etichete accesibile, navigare cu tastatura și layout utilizabil pe mobil.
- Nu introduce textul utilizatorului prin HTML nesigur. Pentru date către JavaScript folosește mecanisme de serializare sigure, precum `json_script`.

## Testare și verificare

- Rulează testele cu interpreterul mediului virtual al proiectului.
- Comanda uzuală: `make test`; alternativă dacă make nu este disponibil: `python manage.py test`.
- Pentru modificări de configurare, rulează și `python manage.py check`.
- Adaugă teste relevante pentru buguri și reguli de business: owner, lună, validare, calcule și protecția datelor.
- Rulează întâi testele vizate, apoi suita completă înainte de a declara etapa terminată.
- Test client-ul Django nu execută JavaScript. Verifică separat deschiderea, anularea, salvarea și erorile modalelor în browser; dacă nu ai acces, indică exact verificarea manuală necesară.
- Nu schimba un rezultat așteptat doar pentru a face testul verde. Actualizează teste când comportamentul convenit s-a schimbat și explică de ce.
- Nu raporta teste sau verificări vizuale ca trecute dacă nu le-ai efectuat.

## Fișiere, migrații și date locale

- Păstrează `db.sqlite3`, `.venv`, fișierele `.env`, cache-urile și secretele în afara Git.
- Nu afișa și nu copia secrete în loguri, documentație sau răspunsuri.
- Nu șterge baza de date și nu recrea datele utilizatoarei ca soluție la un bug fără o cerere explicită.
- Pentru schimbări de modele, creează și verifică migrațiile; păstrează-le în repository.
- Nu elimina migrațiile existente și nu folosi fake migrations ca remediu implicit.
- Folosește date fictive în exemple și teste.

## Terminarea unei sarcini

- Modificări limitate la obiectivul cerut, fără refactorizări fără legătură.
- Explicație scurtă a comportamentului nou și a fișierelor relevante.
- Rezultate reale ale verificărilor și limitele lor.
- Actualizează `POCKETPLAN_ROADMAP.md` numai pentru elementele implementate și verificate; marchează separat blocajele sau verificările manuale restante.
- Lasă modificările pregătite pentru review; operațiile Git externe rămân la cererea explicită a Dianei.
