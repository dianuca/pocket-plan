# PocketPlan — checklist și instrucțiuni pentru Codex

## Scop

Aplicație web de buget personal inspirată dintr-un Excel: venituri, cheltuieli, rate, economii, fond personal lunar, grafice și rapoarte PDF pentru lunile închise.

Repository: https://github.com/dianuca/pocket-plan
Stack convenit: Python, Django 5.2, Django Templates, SQLite, HTML/CSS/JavaScript. Verifică versiunile exacte în proiect.

## Cum lucrăm

- Citește acest fișier, eventualele AGENTS.md, structura proiectului și codul relevant înainte de modificări.
- Verifică ramura curentă și git status. Păstrează modificările existente ale utilizatoarei.
- Folosim GitFlow: develop pentru integrare, main pentru versiuni stabile, feature/* pentru funcționalități și fix/* pentru buguri.
- Creează ramuri din develop actualizat doar când working tree permite acest lucru. Nu muta sau șterge modificări pentru a schimba ramura.
- Diana învață Django: explică în română, cu pași mici, ce schimbi și de ce.
- Lucrează la un singur obiectiv pe rând. Acest roadmap nu autorizează implementarea tuturor etapelor într-o singură cerere.
- Poți modifica fișierele și rula verificările necesare pentru obiectivul cerut.
- Nu face commit, push, merge sau deploy fără o cerere explicită pentru acea acțiune.
- Adaugă teste pentru reguli de business, acces și regresii. Rulează make test; dacă make nu există, folosește python manage.py test cu interpreterul proiectului.
- Nu raporta teste ca trecute dacă nu le-ai executat. Test client-ul Django nu execută JavaScript.
- Nu introduce frameworkuri, dependențe sau refactorizări ample fără a explica necesitatea și a discuta alegerea.
- Actualizează checklist-ul numai după implementare și verificare. Notează separat blocajele.

## Stare cunoscută — de confirmat în cod

Acestea au fost implementate în conversație; nu reprezintă o verificare a ultimei versiuni locale.

- [x] Autentificare și deconectare.
- [x] Venituri, cheltuieli și rate persistate în SQLite.
- [x] Date separate pentru fiecare utilizator.
- [x] Selectarea lunii și rezumat cu venituri, cheltuieli și sold.
- [x] Rate active calculate pe luni și număr de rate rămase.
- [x] Layout modern: sidebar, carduri, tabele și selector lună/an.
- [x] Modale de editare și confirmare de ștergere pentru cele trei module.
- [x] Comanda make test și suită de teste automate (numărul actual trebuie verificat).
- [ ] Confirmă salvarea și erorile în modal pentru toate modulele, inclusiv Venituri.
- [ ] Verifică progresul existent al feature/dashboard-charts: testul și agregarea pe categorii au fost propuse/adăugate, graficele nu au fost confirmate ca terminate.

## 1. Buguri — prioritatea imediată

### Ratele par resetate după adăugare

- [ ] Reproduce: adaugă o rată și observă celelalte înainte și după refresh.
- [ ] Compară luna selectată, URL-ul, răspunsul serverului și valorile din baza de date.
- [ ] Verifică redirectul după salvare: poate schimba luna la prima scadență a ratei noi. Aceasta este o ipoteză, nu cauza confirmată.
- [ ] Clarifică comportamentul dorit: păstrarea lunii consultate sau deschiderea lunii primei scadențe.
- [ ] Corectează cauza confirmată fără să modifici datele istorice accidental.
- [ ] Adaugă test de regresie și verifică și în browser.

### Eroare la ultima cheltuială

- [ ] Obține acțiunea exactă, traceback-ul și pașii de reproducere (adăugare/editare/ștergere).
- [ ] Verifică cazul fără cheltuieli și cazul cu o singură cheltuială.
- [ ] Corectează cauza și adaugă test de regresie.
- [ ] Rulează suita completă.

## 2. Grafice în rezumat — feature/dashboard-charts

- [x] Totaluri de cheltuieli pe categorii, filtrate după owner și luna selectată.
- [x] Include ratele active ca o categorie separată, fără dublare.
- [x] Teste: grupare, alt utilizator, altă lună, lună fără date și rate inactive.
- [x] Grafic pentru distribuția cheltuielilor și comparație venituri–cheltuieli (bare HTML/CSS; verificat prin teste de randare, aspectul rămâne de verificat manual).
- [x] Etichete în română și sume în lei; mesaj explicit când nu există date.
- Transferul către JavaScript nu este necesar: graficele sunt generate în template, fără JavaScript.
- [ ] Verificare vizuală pe desktop și mobil; totalurile graficelor coincid cu rezumatul.

Verificare automată: `make test` — 74 de teste trecute, inclusiv comanda `seed_demo`. Cardurile au înălțime fixă și scroll vertical; aspectul a fost confirmat de Diana în browser. Verificare manuală restantă: acoperirea desktop/mobil, lună fără date, doar venituri, doar cheltuieli și cheltuieli mai mari decât veniturile. Procentele afișate sunt rotunjite independent și pot însuma 99% sau 101%.

## 3. Economii — feature/savings

- [x] Definește soldul inițial și data de început a monitorizării.
- [x] Înregistrează depuneri și retrageri: sumă, dată, descriere și proprietar.
- [x] Sold la o dată = sold inițial + depuneri până atunci − retrageri până atunci (afișat la sfârșitul lunii selectate).
- [x] Afișează depuneri/retrageri lunare, sold acumulat și istoric filtrat pe lună.
- [x] Retragerea finanțează disponibilul lunar; depunerea îl reduce, în luna transferului.
- [x] Nu transforma automat banii rămași în economii; înregistrează explicit transferul.
- [x] Evită numărarea transferurilor interne ca venit sau cheltuială de consum.
- [x] Validează sume, date și politica pentru retrageri peste sold: sunt permise; afișează deficitul necesar revenirii la zero.
- [x] Teste pentru calcule istorice, modificări, izolare și validare.

Implementat: sold inițial cu dată și corectare, depuneri/retrageri cu editare și ștergere, istoric lunar și complet în overlay cu filtre și paginare, sold după fiecare transfer, deficit evidențiat și grafic pe până la 12 luni la finalul paginii.

Reguli: disponibil lunar = venituri − cheltuieli − depuneri + retrageri. Soldul inițial poate fi negativ și nu afectează disponibilul lunar. Transferurile nu pot preceda începutul monitorizării; data inițială nu poate fi mutată după primul transfer. Filtrele istoricului nu schimbă soldurile calculate. Nu există plan automat de recuperare a deficitului pe luni.

Date demo: `python manage.py seed_demo --month 2027-09 --savings --months 12`. Pentru contul pocketplan_demo, adaugă transferuri fără suprascrierea soldului inițial existent; omite datele anterioare începutului monitorizării. Rulările identice nu dublează datele.

Verificare automată: 101 teste trecute, dintre care 23 pentru economii și 7 pentru seed. Graficul și aranjarea butoanelor au fost confirmate de Diana în browser. Rămâne verificarea manuală completă pe mobil și a modalelor: anulare, Escape, validare, salvare, confirmarea ștergerii, filtrare și paginare în overlay. Etapa este implementată funcțional; verificările manuale restante nu sunt declarate terminate.

## 4. Fond personal lunar — feature/personal-budget

- [ ] Sumă alocată pentru fiecare utilizator și lună; o singură alocare pe lună.
- [ ] Marchează o cheltuială ca fiind din fondul personal.
- [ ] Afișează alocat, cheltuit și rămas; permite afișarea unei depășiri.
- [ ] Alocarea este rezervare de bani, nu cheltuială efectivă.
- [ ] Cheltuiala personală intră o singură dată în totalul cheltuielilor.
- [ ] Definește și testează formula pentru banii nealocați după economii și rezerva personală necheltuită.
- [ ] Inițial fond separat pentru fiecare lună; reportarea este opțională și trebuie convenită înainte de implementare.
- [ ] Teste pentru editare/ștergere, schimbarea lunii și evitarea dublei numărări.

## 5. Închiderea lunii — feature/month-closing

- [ ] Buton „Exportă și închide luna”, prin POST și cu confirmare.
- [ ] Salvează un snapshot al raportului: detalii și totaluri, nu doar legături către obiectele modificabile.
- [ ] Snapshot-ul include venituri, cheltuieli, rate, economii și fond personal.
- [ ] Închiderea este atomică și nu creează rapoarte duplicate pentru același utilizator/lună.
- [ ] Blochează modificările datelor lunii închise în backend, nu doar în interfață.
- [ ] Tratează editările care mută date între luni deschise și închise.
- [ ] Definește politica pentru editarea/ștergerea ratelor care afectează mai multe luni.
- [ ] Rapoartele închise rămân identice după modificări ulterioare ale ratelor.
- [ ] Decide împreună politica de redeschidere și regenerare a raportului.
- [ ] Teste pentru acces, blocare, snapshot, repetarea închiderii și integritatea datelor.

## 6. PDF și istoric — feature/monthly-report-pdf

- [ ] Istoric al lunilor închise și vizualizarea fiecărui raport.
- [ ] Descărcare PDF din snapshot, inclusiv pentru luni fără date.
- [ ] Diacritice, monedă, tabele lizibile și paginare.
- [ ] Raportul include luna, totalurile și detaliile financiare convenite.
- [ ] Acces permis doar proprietarului.
- [ ] Teste de răspuns și conținut plus verificare vizuală a PDF-ului.

## 7. Extensii propuse — după funcțiile principale

Acestea sunt idei, nu cerințe deja aprobate pentru implementare.

- [ ] Obiective de economisire și progres.
- [ ] Cheltuieli recurente pentru chirie, utilități și abonamente; fără generări duplicate.
- [ ] Categorii personalizate.
- [ ] Bugete pe categorii și indicator de depășire.
- [ ] Evoluția economiilor și comparații între luni.
- [ ] Reportarea fondului personal nefolosit.

## Reguli comune de date

- Sume calculate cu Decimal; valori financiare valide și monedă inițială lei.
- Fiecare lookup și agregare trebuie limitate la utilizatorul autentificat.
- Owner se stabilește pe server, niciodată din POST.
- Păstrează CSRF; acțiunile de modificare/ștergere se fac prin POST.
- SQLite și datele locale nu se trimit în Git; păstrează db.sqlite3, .venv și secretele ignorate.
- Nu șterge baza de date pentru a rezolva o eroare fără o cerere explicită.
- Păstrează migrațiile în repository.

## Criterii pentru terminarea fiecărei etape

- [ ] Comportamentul convenit este implementat și explicat.
- [ ] Testele relevante și suita completă trec.
- [ ] Interfața a fost verificată manual dacă etapa afectează JavaScript sau aspectul.
- [ ] Sunt documentate limitările și pașii de verificare.
- [ ] Checklist-ul reflectă rezultatul real.
- [ ] Commit/PR/merge se fac doar la cererea Dianei.

## Primul mesaj pentru Codex

> Citește POCKETPLAN_ROADMAP.md și instrucțiunile repository-ului. Verifică ramura, git status și codul existent. Începem cu bugurile din etapa 1. Investighează cauzele și spune-mi ce pași de reproducere lipsesc. Nu implementa întregul roadmap și nu face commit/push/merge. După diagnostic, lucrăm la o corecție mică, explicată, cu test de regresie.
