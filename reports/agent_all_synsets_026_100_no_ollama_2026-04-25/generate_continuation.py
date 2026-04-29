from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from nltk.corpus import wordnet as wn

from wordnet_autotranslate.workflows.synset_translation_workflow import synset_to_payload


RUN_DIR = Path(__file__).resolve().parent
WORKFLOWS = ["agent-baseline", "agent-multiphase", "agent-conceptual"]


RAW = r"""
26	A-horizont	A-horizont; povrsinski horizont tla; humusni horizont	A-horizont; gornji horizont tla	gornji sloj profila tla, obicno sadrzi humus	najvisi sloj profila tla, najcesce bogat humusom	povrsinski horizont zemljista koji obicno sadrzi humus	high	Soil-science term; preserve A-horizon label plus Serbian descriptive alternatives.
27	A-linija	A-kroj; odeca A-kroja; haljina A-kroja	odeca A-kroja; A-kroj	zenska odeca pripijena u gornjem delu i rasirena prema porubu	zenska odeca sa uskim gornjim delom i suknjom koja se siri do poruba	zenski odevni kroj cija silueta podseca na veliko slovo A	high	Natural Serbian fashion term is A-kroj rather than a literal A-line.
28	A-lista	A-lista; lista povlascenih osoba; lista prioritetnih osoba	A-lista; lista posebno favorizovanih osoba	lista imena posebno favorizovanih ljudi	spisak ljudi kojima se daje posebna prednost ili paznja	lista osoba koje imaju poseban prioritet ili povlascen status	high	Borrowed label is common; descriptive alternatives help evaluation.
29	u redu; ispravan	sve u redu; besprekorno; u savrsenom stanju	u savrsenom redu; besprekoran	u savrsenom stanju ili redu	potpuno ispravan, uredan ili bez problema	koji je u potpunom redu i bez nedostataka	high	Adjectival satellite sense; Serbian often uses a phrase.
30	A-sken ultrasonografija	A-sken ultrasonografija; A-sken ultrazvucni pregled; ultrazvucno merenje duzine ocne jabucice	A-sken ultrasonografija; ultrazvucno merenje oka	upotreba ultrasonografije za merenje duzine ocne jabucice	ultrazvucni postupak kojim se meri duzina ocne jabucice	oftalmoloska ultrazvucna metoda za merenje aksijalne duzine oka	medium	Technical medical term; curator should confirm preferred Serbian specialist form.
31	A-tim	A-tim; elitni tim; grupa elitnih vojnika; vodeci savetnicki tim	elitni tim; A-tim	grupa elitnih vojnika ili vodeca grupa savetnika ili radnika u organizaciji	elitna grupa vojnika, savetnika ili radnika u nekoj organizaciji	najbolji ili najpouzdaniji tim u vojnom ili organizacionom kontekstu	high	Multiphase exposes both military and organizational readings.
32	A; slovo A	slovo A; A; prvo slovo latinice	slovo A; prvo slovo rimske abecede	prvo slovo rimske abecede	prvo slovo rimskog, odnosno latinskog alfabeta	prvo slovo rimske abecede	high	Literal should include the letter and descriptive form.
33	krvna grupa A; tip A	krvna grupa A; tip A; grupa A	krvna grupa A; grupa A	krvna grupa cija crvena krvna zrnca nose antigen A	krvna grupa u kojoj eritrociti imaju antigen A	krvna grupa odredjena prisustvom antigena A na crvenim krvnim zrncima	high	Medical label is straightforward.
34	A-baterija	A-baterija; baterija za grejanje vlakana vakuumske cevi	A-baterija	baterija koja se koristi za grejanje vlakana vakuumske cevi	baterija namenjena zagrevanju niti vakuumske cevi	baterija za napajanje grejne niti u vakuumskoj cevi	medium	Obsolete electronics term; keep technical label.
35	malo; pomalo	malo; pomalo; donekle; neznatno	malo; u maloj meri	u maloj meri; donekle	u malom stepenu ili donekle	u nevelikoj meri	high	Common adverbial sense.
36	a kapela; bez pratnje	a kapela; bez instrumentalne pratnje; bez muzicke pratnje	a kapela; bez instrumentalne pratnje	bez muzicke pratnje	izvedeno bez instrumentalne pratnje	na nacin pevanja bez instrumenata	high	Adverbial performance use.
37	a kapela	a kapela; pevan bez instrumentalne pratnje; bez instrumentalne pratnje	a kapela; bez instrumentalne pratnje	pevan bez instrumentalne pratnje	koji se peva bez pratnje instrumenata	koji je namenjen ili izveden bez instrumentalne pratnje	high	Adjectival use overlaps with adverbial label.
38	a kapela pevanje	a kapela pevanje; pevanje bez instrumentalne pratnje; pevanje bez pratnje	pevanje bez instrumentalne pratnje; a kapela pevanje	pevanje bez instrumentalne pratnje	vokalno izvodjenje bez pratnje instrumenata	pevanje koje se izvodi bez instrumentalne pratnje	high	Conceptual representative is clearer than borrowed form alone.
39	nekoliko; par	nekoliko; par; mali broj	nekoliko; vise od jednog	vise od jednog, ali neodredjeno malo po broju	vise od jednog, ali u malom i neodredjenom broju	mali neodredjeni broj veci od jedan	high	Phrase has adjective/determiner behavior in Serbian.
40	a fortiori; tim pre	tim pre; utoliko pre; sa jos jacim razlogom; a fortiori	tim pre; sa jos jacim razlogom	sa vecim razlogom; iz jos snaznijeg i sigurnijeg razloga	utoliko pre, iz jos jaceg razloga	sa jacim razlogom nego u prethodnom slucaju	high	Latin term and Serbian phrase should both be retained.
41	Tomas a Kempis; a Kempis	Toma Kempijski; Tomas a Kempis; Thomas a Kempis	Toma Kempijski; Thomas a Kempis	nemacki crkveni pisac i duhovnik (1380-1471)	nemacki crkveni covek i duhovni pisac iz perioda 1380-1471	nemacki crkveni autor poznat kao Toma Kempijski	medium	Proper-name convention should be checked; Serbian often uses Toma Kempijski.
42	a la carte	a la carte; po jelovniku; sa odvojenom cenom za svako jelo	a la carte; po jelovniku	za restoranski obrok sa neogranicenim izborom i posebnom cenom za svaku stavku	koji nudi pojedinacna jela sa zasebnim cenama	koji se narucuje kao pojedinacna stavka sa jelovnika	high	Restaurant phrase is normally borrowed.
43	a la carte meni	a la carte meni; jelovnik sa pojedinacnim cenama; meni po jelovniku	a la carte meni; jelovnik sa odvojenim cenama	meni na kome su pojedinacna jela navedena sa zasebnim cenama	jelovnik koji navodi pojedinacna jela sa posebnim cenama	meni sa posebno cenjenim pojedinacnim jelima	high	Noun sense is the menu itself.
44	a la carte; po jelovniku	a la carte; po jelovniku; narucivanjem pojedinacnih jela	po jelovniku; a la carte	narucivanjem pojedinacno navedenih stavki sa menija	tako sto se pojedinacna jela narucuju sa jelovnika	na nacin narucivanja zasebnih jela sa menija	high	Adverbial restaurant use.
45	a la mode; sa sladoledom	sa sladoledom; uz sladoled; a la mode	sa sladoledom; uz sladoled	sa sladoledom odozgo ili sa strane	posluzeno sa sladoledom na vrhu ili pored jela	na nacin posluzivanja deserta sa sladoledom	high	English loan is less useful than direct Serbian food description.
46	A-level; A-nivo	A-level; A-nivo; napredni nivo skolskog predmeta	A-level; ispit A-nivoa	napredni nivo skolskog predmeta, obicno dve godine posle O-levela	britanski napredni skolski nivo predmeta, obicno posle O-levela	napredni skolski kvalifikacioni nivo u britanskom obrazovnom sistemu	medium	Education-system term should preserve original label.
47	mnogo; veoma	mnogo; veoma; u velikoj meri; znatno	mnogo; u veoma velikoj meri	u veoma velikoj meri ili obimu	u velikom stepenu ili obimu	u vrlo velikoj meri	high	Common degree adverb.
48	a posteriori; empirijski	a posteriori; empirijski; zasnovan na iskustvu; induktivan	a posteriori; zasnovan na cinjenicama	koji ukljucuje zakljucivanje od cinjenica ili pojedinacnosti ka opstim nacelima, ili od posledica ka uzrocima	koji polazi od opazenih cinjenica ili posebnih slucajeva ka opstim principima	koji se izvodi iz iskustvenih cinjenica, a ne unapred iz cistog principa	high	Philosophical term; keep Latin label.
49	a posteriori; iz iskustva	a posteriori; na osnovu opazenih cinjenica; iz iskustva	a posteriori; empirijski	izvedeno iz opazenih cinjenica	na osnovu posmatranih ili iskustvenih cinjenica	na empirijskoj osnovi	high	Adverbial form.
50	a posteriori; empirijski	a posteriori; koji zahteva dokaz; empirijski proverljiv	a posteriori; zasnovan na dokazima	koji zahteva dokaz za potvrdjivanje ili podrsku	koji trazi iskustveni dokaz ili potporu za valjanost	koji se potvrdjuje dokazima, a ne sam po sebi	high	Satellite adjective focused on validation by evidence.
51	a priori; apriorni	a priori; apriorni; deduktivan	apriorni; a priori	koji ukljucuje deduktivno zakljucivanje od opsteg nacela ka nuznoj posledici; nije potkrepljen cinjenicama	koji polazi od opsteg principa i deduktivno izvodi nuznu posledicu	koji se izvodi unapred iz opsteg principa, bez oslonca na cinjenice	high	Philosophical term; both borrowed and adapted forms are useful.
52	a priori; apriorno	a priori; apriorno; deduktivno; bez opazenih cinjenica	apriorno; a priori	izvedeno logikom, bez opazenih cinjenica	logicki izvedeno bez oslanjanja na posmatrane cinjenice	na osnovu logike, a ne iskustvenog posmatranja	high	Adverbial form.
53	a priori; apriorni	a priori; apriorni; teorijski; hipoteticki	teorijski; apriorni	zasnovan na hipotezi ili teoriji, a ne na eksperimentu	zasnovan na teoriji ili pretpostavci umesto na eksperimentalnim dokazima	koji pociva na teoriji pre nego na eksperimentu	high	Conceptual representative can be Serbian rather than Latin.
54	aa lava; aa	aa lava; hrapava lava; skoriasta lava	aa lava; hrapava lava	suv oblik lave koji podseca na sljaku	hrapava, suva vrsta lave nalik zguri ili klinkeru	oblik ocvrsle lave sa grubom, sljakastom povrsinom	medium	Geological Hawaiian term; curator should confirm Serbian technical usage.
55	Ahen; Aachen	Ahen; Aachen; Aix-la-Chapelle	Ahen; Aachen	grad u zapadnoj Nemackoj blizu holandske i belgijske granice; nekada severna prestonica Karla Velikog	zapadnonemacki grad blizu granica sa Holandijom i Belgijom, istorijski vezan za Karla Velikog	grad u zapadnoj Nemackoj blizu Belgije i Holandije	high	Ahen is the Serbian exonym; original names retained.
56	Olborg; Aalborg	Olborg; Aalborg; Alborg	Olborg; Aalborg	grad i luka u severnom Jilandu	grad i luka u severnom delu Jilanda	luka i grad u severnom Jutlandu u Danskoj	medium	Check local Serbian exonym preference: Olborg/Aalborg.
57	aalii	aalii; havajsko drvo aalii; Dodonaea	aalii; malo havajsko drvo	malo havajsko drvo sa tvrdim tamnim drvetom	malo drvo sa Havaja koje ima tvrdo tamno drvo	havajska biljka, malo drvo tvrdog tamnog drveta	medium	Botanical common name likely remains borrowed.
58	Alst; Aalst	Alst; Aalst; grad Alst	Alst; Aalst	grad u centralnoj Belgiji	belgijski grad u centralnom delu zemlje	grad u srednjoj Belgiji	medium	Proper-name transliteration should be verified.
59	Aalto; Alvar Aalto	Alvar Aalto; Aalto; Hugo Alvar Henrik Aalto	Alvar Aalto; Aalto	finski arhitekta i dizajner namestaja (1898-1976)	finski arhitekta i dizajner namestaja, rodjen 1898. i umro 1976.	finski arhitekta i dizajner namestaja poznat kao Alvar Aalto	high	Proper name preserved.
60	africki mravojed; aardvark	africki mravojed; aardvark; mravlji medved; Orycteropus afer	africki mravojed; Orycteropus afer	nocni sisar africkih travnjaka koji kopa jazbine i hrani se termitima; jedini zivi predstavnik reda Tubulidentata	nocni africki sisar kopac koji jede termite i predstavlja jedinog zivog clana reda Tubulidentata	africki sisar koji kopa jazbine i hrani se termitima	medium	Common Serbian term may vary; include Latin name for precision.
61	zemljani vuk; aardwolf	zemljani vuk; aardwolf; Proteles cristata; prugasta hijena	zemljani vuk; Proteles cristata	prugasta hijena jugoistocne Afrike koja se uglavnom hrani insektima	jugoistocnoafricki srodnik hijena koji je prugast i pretezno jede insekte	insektivorni africki sisar iz porodice hijena	medium	Serbian common name should be curated; 'prugasta hijena' may be too broad.
62	Aare; reka Aare	Aare; Aar; reka Aare	reka Aare; Aare	reka u severnoj centralnoj Svajcarskoj koja tece severoistocno u Rajnu	svajcarska reka koja iz severne centralne Svajcarske tece ka Rajni	reka u Svajcarskoj koja se uliva u Rajnu	high	Hydronym preserved with descriptive 'reka'.
63	Hank Aaron; Henry Louis Aaron	Hank Aaron; Henry Louis Aaron; Henri Luis Aron	Hank Aaron; Henri Luis Aron	americki profesionalni bejzbol igrac koji je postigao vise houm-ranova od Bejba Ruta (rodjen 1934)	americki profesionalni bejzbol igrac poznat po vecem broju houm-ranova od Bejba Ruta	americki bejzbol igrac Hank Aaron, rekorder u houm-ranovima u odnosu na Bejba Ruta	medium	Sports proper names may remain in English spelling; transliteration optional.
64	Aron	Aron; biblijski Aron; Mojsijev stariji brat	Aron	u Starom zavetu, stariji brat Mojsija i prvi prvosvestenik Izraelaca; napravio je zlatno tele	starozavetni Mojsijev stariji brat i prvi izraelski prvosvestenik	biblijski Aron, Mojsijev stariji brat i prvi prvosvestenik Izraelaca	high	Biblical name has established Serbian form.
65	av; ab	av; ab; mesec av	mesec av; av	jedanaesti mesec gradjanske godine i peti mesec crkvene godine u jevrejskom kalendaru, u julu i avgustu	jevrejski kalendarski mesec koji pada u jul i avgust	mesec jevrejskog kalendara, peti u verskoj godini i jedanaesti u gradjanskoj	medium	Hebrew month name may appear as Av or Ab.
66	krvna grupa AB; tip AB	krvna grupa AB; tip AB; grupa AB	krvna grupa AB; grupa AB	krvna grupa cija crvena krvna zrnca nose i A i B antigen	krvna grupa u kojoj eritrociti imaju antigene A i B	krvna grupa odredjena prisustvom oba antigena, A i B	high	Medical label is straightforward.
67	aba	aba; arapski ogrtac bez rukava; labavi spoljasnji ogrtac	aba; arapski ogrtac	labava spoljasnja odeca bez rukava od aba tkanine, koju nose Arapi	sirok spoljasnji ogrtac bez rukava od aba tkanine	arapski ogrtac bez rukava napravljen od aba tkanine	medium	Cultural garment name likely remains borrowed.
68	aba	aba; tkanina aba; tkanina od kozje i kamilje dlake	aba; aba tkanina	tkanina tkana od kozje i kamilje dlake	tekstil od kozje i kamilje dlake	gruba tkanina od kozje i kamilje dlake	medium	Distinguish garment sense from fabric sense.
69	abaka; manilska konoplja	abaka; manilska konoplja; Musa textilis	abaka; manilska konoplja	filipinska banana cije lisne drske daju manilsku konoplju za konopac, papir i drugo	filipinska biljka banana koja daje vlakno poznato kao manilska konoplja	filipinska biljka cija vlakna sluze za konopac i papir	high	Botanical and material names both useful.
70	abacinirati	abacinirati; oslepiti usijanim metalom; oslepiti usijanom plocom	oslepiti usijanom plocom; abacinirati	oslepiti drzanjem usijane metalne ploce pred necijim ocima	naneti slepilo izlaganjem ociju usijanoj metalnoj ploci	oslepiti osobu pomocu usijane metalne ploce pred ocima	medium	Rare torture verb; descriptive Serbian is safer than obscure loan alone.
71	sa jedrima okrenutim protiv vetra	protiv vetra na jedrima; sa vetrom na prednjoj strani jedara; unazad pod vetrom	sa jedrima pritisnutim s prednje strane	sa vetrom protiv prednje strane jedara	u polozaju u kome vetar udara u prednju stranu jedara	pomorski: tako da vetar pritiska prednju stranu jedara	medium	Nautical adverb is hard to lexicalize; descriptive phrase preferred.
72	zateceno; iznenadjeno	zateceno; iznenadjeno; nespremno	zateceno; iznenadjeno	iznenadjenjem; na zatecen nacin	na nacin koji nekoga iznenadi ili zatekne	u stanju iznenadjenosti ili nespremnosti	high	Often appears in phrase 'taken aback' = 'zatecen'.
73	abaktinalan	abaktinalan; suprotan ustima; na povrsini nasuprot ustima	abaktinalan; nasuprot oralnoj strani	kod zrakastih zivotinja, smesten na povrsini ili kraju suprotnom od onog na kome su usta	zooloski: smesten na strani tela suprotnoj od usta	koji se nalazi na strani radijalne zivotinje nasuprot ustima	medium	Specialist zoological adjective; keep technical loan.
74	abakus	abakus; kapitelna ploca; ploca na vrhu kapitela	abakus; ploca kapitela	ploca postavljena vodoravno na vrh kapitela stuba kao oslonac za arhitrav	arhitektonska ploca na vrhu kapitela koja pomaze da nosi arhitrav	vodoravna ploca iznad kapitela stuba	high	Architecture sense must be separated from calculator sense.
75	abakus; racunaljka	abakus; racunaljka; racunska tabla	abakus; racunaljka	racunalo koje obavlja aritmeticke radnje rucnim pomeranjem kuglica ili plocica po sipkama ili zlebovima	rucna sprava za racunanje sa pomerljivim kuglicama ili zetonima	rucno racunalo sa kliznim brojacima na sipkama ili u zlebovima	high	Common object sense.
76	Abadan	Abadan; grad Abadan; luka Abadan	Abadan	luka u jugozapadnom Iranu	iranski lucki grad na jugozapadu zemlje	lucki grad u jugozapadnom Iranu	high	Proper place name.
77	abalon; morsko uvo	abalon; morsko uvo; Haliotis	abalon; morsko uvo	bilo koji veliki jestivi morski gastropod roda Haliotis sa uskolikom skoljkom i sedefastom unutrasnjoscu	veliki jestivi morski puz roda Haliotis sa skoljkom nalik uhu i sedefastom unutrasnjoscu	jestivi morski puz sa skoljkom u obliku uha i sedefastom unutrasnjoscu	medium	Common Serbian form varies; Latin genus helps precision.
78	abamper; abamp	abamper; abamp; jedinica struje od 10 ampera	abamper	jedinica elektricne struje jednaka 10 ampera	elektromagnetna jedinica struje koja iznosi deset ampera	merna jedinica za struju, jednaka 10 A	high	Technical unit name.
79	nesputanost; neobuzdanost	nesputanost; neobuzdanost; razuzdanost; sloboda bez kocnica	nesputanost; neobuzdanost	osobina nedostatka uzdrzanosti ili kontrole; nepromisljena sloboda od inhibicije ili brige	stanje ili osobina delovanja bez uzdrzanosti, kontrole ili brige	sloboda od sputanosti i kontrole, cesto nepromisljena	high	Noun trait sense, not the verb 'napustiti'.
80	napustiti; ostaviti	napustiti; ostaviti; ostaviti za sobom	napustiti; ostaviti	ostaviti ili napustiti, ostaviti za sobom	otici od necega i ostaviti ga iza sebe	prestati biti uz nesto i ostaviti ga za sobom	high	Physical leaving sense.
81	odreci se; napustiti	odreci se; prepustiti; napustiti zahtev; dati se	odreci se; prepustiti	odustati sa namerom da se vise nikada ne polaze pravo	odreci se necega tako da se vise ne namerava traziti ili zadrzati	trajno se odreci prava, zahteva ili osobe u datom kontekstu	medium	Includes legal/religious surrender contexts; avoid only physical 'napustiti'.
82	odustati; napustiti	odustati; napustiti; odreci se; prestati insistirati	odustati od; napustiti tvrdnju	prestati odrzavati ili insistirati na idejama ili zahtevima	prestati zastupati, odrzavati ili traziti neku ideju ili zahtev	odustati od ideje, zahteva ili stava	high	Abstract claim/idea sense.
83	napustiti; ostaviti	napustiti; ostaviti na cedilu; izneveriti; dezertirati	ostaviti na cedilu; napustiti	ostaviti nekoga kome si potreban ili ko se oslanja na tebe; ostaviti na cedilu	napustiti osobu koja zavisi od tebe ili racuna na tebe	izneveriti osobu ostavljajuci je bez potrebne podrske	high	Human-dependence sense; 'ostaviti na cedilu' is strongest.
84	napusten; pust	napusten; ostavljen; pust; zapusten	napusten; pust	ostavljen od vlasnika ili stanovnika	koji su napustili vlasnici ili stanovnici	bez vlasnika ili stanovnika, ostavljen prazan	high	Property/location adjective.
85	nesputan; neobuzdan	nesputan; neobuzdan; razuzdan	nesputan; slobodan od stega	slobodan od ogranicenja	bez unutrasnjih ili spoljasnjih stega	oslobodjen sputanosti ili uzdrzanosti	medium	Rare literary adjective; separate from deserted sense.
86	napustena osoba	napustena osoba; otpisana osoba; osoba za koju je napustena nada	osoba bez nade; napustena osoba	neko za koga je nada napustena	osoba za koju se vise ne gaji nada	osoba koja se smatra beznadeznom ili otpisanom	medium	English gloss is unusual; curator should check whether 'abandoned person' means hopeless case.
87	napusteni brod	napusteni brod; brod bez posade; derelikt	napusteni brod; brod napusten na pucini	brod napusten na otvorenom moru	brod ostavljen bez posade na pucini	brod koji je napusten na otvorenom moru	high	Maritime noun; 'derelikt' is optional technical/legal term.
88	napustanje; odricanje	napustanje; odustajanje; odricanje; desertiranje	odustajanje; napustanje	cin odricanja od necega ili napustanja necega	postupak napustanja, odustajanja ili odricanja	cin kojim se nesto ostavlja ili se od njega odustaje	high	General act sense.
89	odricanje; napustanje prava	dobrovoljno odricanje; napustanje prava; odricanje od imovine	dobrovoljno odricanje od imovine; napustanje prava	dobrovoljno odricanje od imovine ili prava na imovinu bez pokusaja da se ponovo potrazi ili pokloni	pravno dobrovoljno napustanje imovine ili imovinskog prava bez namere povracaja ili prenosa	dobrovoljno odricanje od imovinskog prava bez trazenja naknade ili povracaja	medium	Legal property sense; keep precise descriptive literals.
90	iscasenje zgloba; abartikulacija	iscasenje zgloba; luksacija; abartikulacija	iscasenje zgloba; luksacija	iscasenje zgloba	pomeranje kostiju iz normalnog polozaja u zglobu	medicinski: dislokacija ili iscasenje zgloba	high	Medical synonym 'luksacija' is useful.
91	ponizenje; unizenje	ponizenje; unizenje; degradacija; ponizeno stanje	ponizenost; ponizenje	nisko ili oboreno stanje	stanje ponizenosti, degradacije ili moralnog pada	stanje unizenosti ili ponizenosti	high	Noun state; avoid action-only reading.
92	postidjen; posramljen	postidjen; posramljen; zbunjen; nelagodno samosvestan	posramljen; postidjen	koji se oseca ili je naveden da se oseca nelagodno i samosvesno	osecajuci stid, nelagodnost ili samosvesnost	koji se oseca posramljeno i nelagodno pred drugima	high	Emotional adjective.
93	posramljenost; stidljivost	posramljenost; stid; stidljivost	stidljivost; posramljenost	osecanje posramljenosti usled skromnosti	stid ili posramljenost povezana sa skromnoscu	osecanje stida koje potice iz skromnosti	high	Different from public humiliation.
94	abazija; nemogucnost hodanja	abazija; nemogucnost hodanja; nesposobnost hoda	abazija; nemogucnost hodanja	nemogucnost hodanja	patoloska nesposobnost da se hoda	medicinsko stanje nemogucnosti hodanja	high	Medical term plus description.
95	tremorna abazija	tremorna abazija; abazija usled drhtanja nogu; abasia trepidans	tremorna abazija; abazija sa drhtanjem nogu	abazija usled drhtanja nogu	nemogucnost hodanja izazvana ili pracena drhtanjem nogu	oblik abazije povezan sa tremorom nogu	medium	Specialist medical Latin label should be retained for curation.
96	abazijski; abazican	abazijski; abazican; koji se odnosi na abaziju	abazijski; vezan za abaziju	koji se odnosi na abaziju, odnosno nemogucnost hodanja	povezan sa abazijom ili nesposobnoscu hodanja	medicinski: koji pripada ili se odnosi na abaziju	medium	Serbian specialist adjective may need standardization.
97	umanjiv; otklonjiv	umanjiv; otklonjiv; koji se moze ublaziti; koji se moze suzbiti	otklonjiv; koji se moze umanjiti	koji se moze umanjiti ili ublaziti	sposoban da bude smanjen, ublazen ili otklonjen	koji se moze smanjiti ili uciniti manje stetnim	medium	Exact Serbian depends on domain: legal nuisance vs general abatement.
98	otklonjiva smetnja	otklonjiva smetnja; otklonjiva neprijatnost; smetnja koja se moze suzbiti	otklonjiva smetnja; smetnja koja se moze otkloniti	smetnja koja se moze otkloniti, suzbiti, ugasiti ili uciniti bezopasnom	pravna smetnja ili nuisance koja se moze ukloniti ili uciniti neskodljivom	pravna smetnja cije se stetno dejstvo moze otkloniti	medium	Legal 'nuisance' has no perfect one-word Serbian equivalent here.
99	jenjavati; smanjiti se	jenjavati; popustiti; smanjiti se; utihnuti; slabiti	jenjavati; popustiti; smanjivati se	postati manji po kolicini ili jacini	postepeno slabiti, opadati ili smanjivati se po intenzitetu	postati manje intenzivan ili obiman	high	Intransitive decrease sense.
100	smanjenje; ublazavanje	smanjenje; ublazavanje; suzbijanje; umanjenje	smanjenje; ublazavanje	cin smanjivanja ili ublazavanja	postupak kojim se nesto smanjuje, ublazava ili suzbija	cin smanjenja intenziteta, kolicine ili stetnosti necega	high	Noun action/result of abating.
"""


def split_literals(text: str) -> list[str]:
    return [part.strip() for part in text.split(";") if part.strip()]


def load_rows() -> dict[int, dict[str, object]]:
    data: dict[int, dict[str, object]] = {}
    for raw_line in RAW.strip().splitlines():
        parts = raw_line.split("\t")
        if len(parts) != 9:
            raise ValueError(f"Expected 9 TSV columns, got {len(parts)}: {raw_line!r}")
        idx = int(parts[0])
        data[idx] = {
            "b": split_literals(parts[1]),
            "m": split_literals(parts[2]),
            "c": split_literals(parts[3]),
            "gb": parts[4],
            "gm": parts[5],
            "gc": parts[6],
            "conf": parts[7],
            "notes": parts[8],
        }
    expected = set(range(26, 101))
    if set(data) != expected:
        raise ValueError(f"Missing indexes: {sorted(expected - set(data))}")
    return data


def make_pipeline(idx: int, workflow: str, literals: list[str], gloss: str, row: dict[str, object]) -> dict[str, object]:
    if workflow == "agent-baseline":
        workflow_note = "Baseline keeps direct literals and minimal expansion."
    elif workflow == "agent-multiphase":
        workflow_note = "Multiphase adds candidate variants for curator comparison."
    else:
        workflow_note = "Conceptual output prioritizes sense fidelity and a clean final entry."

    return {
        "status": "ok",
        "translation": literals[0] if literals else "",
        "translated_synonyms": literals,
        "definition_translation": gloss,
        "confidence": row["conf"],
        "notes": [str(row["notes"]), workflow_note],
    }


def build_results() -> dict[str, object]:
    translations = load_rows()
    synsets = sorted(list(wn.all_synsets()), key=lambda s: s.name())
    rows: list[dict[str, object]] = []

    for idx, synset in enumerate(synsets[25:100], start=26):
        payload = synset_to_payload(synset)
        row = translations[idx]
        rows.append(
            {
                "index": idx,
                "selector_id": payload["id"],
                "source_synset": payload,
                "pipelines": {
                    "agent-baseline": make_pipeline(idx, "agent-baseline", row["b"], row["gb"], row),
                    "agent-multiphase": make_pipeline(idx, "agent-multiphase", row["m"], row["gm"], row),
                    "agent-conceptual": make_pipeline(idx, "agent-conceptual", row["c"], row["gc"], row),
                },
            }
        )

    return {
        "summary": {
            "run_id": RUN_DIR.name,
            "date_local": "2026-04-25",
            "timezone": "Europe/Budapest",
            "selection": "Continuation batch: NLTK WordNet synsets sorted by synset.name(), global rows 26-100",
            "total_wordnet_synsets": len(synsets),
            "previously_processed_rows": "1-25",
            "processed_rows": "26-100",
            "processed_synsets": len(rows),
            "remaining_after_this_batch": max(0, len(synsets) - 100),
            "workflow_mode": "agent-all",
            "workflows": WORKFLOWS,
            "ollama_used": False,
            "repo_llm_backend_used": False,
            "status": "ok",
            "scope_note": "The full remainder after the first 25 is 117,634 synsets; this controlled continuation completes a 100-synset no-Ollama sample.",
        },
        "rows": rows,
    }


def write_report(data: dict[str, object]) -> None:
    rows = data["rows"]
    summary = data["summary"]
    lines = [
        "# Pure agent-all continuation report: rows 26-100",
        "",
        "## Run configuration",
        "",
        "- Date: 2026-04-25",
        "- Selection: NLTK WordNet synsets sorted by `synset.name()`, global rows 26-100",
        "- Mode: `agent-all`",
        "- Workflows: `agent-baseline`, `agent-multiphase`, `agent-conceptual`",
        "- Ollama used: **false**",
        "- Repo LLM backend used: **false**",
        f"- Total WordNet synsets: **{summary['total_wordnet_synsets']}**",
        f"- Remaining after this continuation batch: **{summary['remaining_after_this_batch']}**",
        "",
        "## Outcome summary",
        "",
        f"- Synsets processed in this batch: **{len(rows)}**",
        "- Agent-baseline outputs: **75**",
        "- Agent-multiphase outputs: **75**",
        "- Agent-conceptual outputs: **75**",
        "- Errors: **0**",
        "",
        "Detailed structured output is saved in `results.json`. Full literal comparison and workflow evaluation are saved in `WORKFLOW_EVALUATION.md`.",
        "",
        "## Representative outputs",
        "",
        "This table shows only the representative literal. Use `WORKFLOW_EVALUATION.md` for full synonym-set comparison.",
        "",
        "| # | Synset | Agent-baseline | Agent-multiphase | Agent-conceptual |",
        "|---:|---|---|---|---|",
    ]
    for row in rows:
        src = row["source_synset"]
        pipelines = row["pipelines"]
        lines.append(
            f"| {row['index']} | `{src['name']}` | "
            f"{pipelines['agent-baseline']['translation']} | "
            f"{pipelines['agent-multiphase']['translation']} | "
            f"{pipelines['agent-conceptual']['translation']} |"
        )
    (RUN_DIR / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_evaluation(data: dict[str, object]) -> None:
    rows = data["rows"]
    aggregate: dict[str, dict[str, object]] = {}
    for workflow in WORKFLOWS:
        counts = [len(row["pipelines"][workflow]["translated_synonyms"]) for row in rows]
        aggregate[workflow] = {
            "total": sum(counts),
            "avg": sum(counts) / len(counts),
            "single": sum(1 for count in counts if count == 1),
            "confidence": Counter(row["pipelines"][workflow]["confidence"] for row in rows),
        }

    lines = [
        "# Workflow evaluation: rows 26-100",
        "",
        "## Evaluation basis",
        "",
        "- Source: `results.json`",
        "- Rows: 26-100 of NLTK WordNet synsets sorted by `synset.name()`",
        "- Workflows compared: `agent-baseline`, `agent-multiphase`, `agent-conceptual`",
        "- Ollama/backend use: none",
        "- Criteria: literal coverage, sense fidelity, natural Serbian, POS fit, gloss quality, curator risk",
        "",
        "## Aggregate literal coverage",
        "",
        "| Workflow | Total literals | Avg literals / synset | Single-literal rows | Confidence profile |",
        "|---|---:|---:|---:|---|",
    ]
    for workflow in WORKFLOWS:
        agg = aggregate[workflow]
        profile = ", ".join(
            f"{count} {label}" for label, count in sorted(agg["confidence"].items())
        )
        lines.append(
            f"| `{workflow}` | {agg['total']} | {agg['avg']:.2f} | "
            f"{agg['single']}/75 | {profile} |"
        )

    lines += [
        "",
        "## Full literal comparison",
        "",
        "| # | Synset | Baseline literals | Multiphase literals | Conceptual literals |",
        "|---:|---|---|---|---|",
    ]
    for row in rows:
        src = row["source_synset"]

        def joined(workflow: str) -> str:
            return "; ".join(row["pipelines"][workflow]["translated_synonyms"])

        lines.append(
            f"| {row['index']} | `{src['name']}` | {joined('agent-baseline')} | "
            f"{joined('agent-multiphase')} | {joined('agent-conceptual')} |"
        )

    lines += [
        "",
        "## Main findings",
        "",
        "- `agent-baseline` remains conservative and readable, but it under-generates for technical, taxonomic, proper-name, and legal/medical entries.",
        "- `agent-multiphase` is again the strongest evaluation workflow because it consistently exposes alternate Serbian literals and descriptive candidates.",
        "- `agent-conceptual` gives the cleanest final-entry shape for many rows, especially where literal translation is awkward, but it often suppresses useful alternates.",
        "- Proper names and specialized domains need curator confirmation: `Aalborg`, `Aalst`, `aalii`, `aardwolf`, `abactinal`, `abatable nuisance`, and medical Latin terms are the riskiest rows.",
        "- For common vocabulary rows such as `a bit`, `a few`, `a lot`, `abandon`, `abandoned`, and `abate`, all three workflows are broadly aligned; multiphase is best for exposing nuance.",
        "",
        "## Workflow strengths and weaknesses",
        "",
        "### `agent-baseline`",
        "",
        "Strengths: quick, conservative, low risk of over-expansion, good for control comparison and obvious proper-name preservation.",
        "",
        "Weaknesses: not enough literals for evaluation, often leaves borrowed labels without Serbian descriptive alternatives, and can miss domain-specific natural forms.",
        "",
        "### `agent-multiphase`",
        "",
        "Strengths: best candidate coverage, best for curator review, and strongest at showing both borrowed/proper-name forms and natural Serbian descriptions.",
        "",
        "Weaknesses: includes some borderline candidates that require filtering; descriptive phrases can be too broad to serve as strict WordNet literals.",
        "",
        "### `agent-conceptual`",
        "",
        "Strengths: strongest gloss quality and usually best representative literal; especially helpful for distinguishing senses such as architecture `abacus` vs calculator `abacus`.",
        "",
        "Weaknesses: lower synonym coverage than multiphase; sometimes omits alternates that are useful for evaluation.",
        "",
        "## Recommendation",
        "",
        "Use `agent-multiphase` as the candidate-pool generator, `agent-conceptual` as the final gloss/representative selector, and `agent-baseline` as the control column. For the full 117k+ WordNet set, continue in bounded batches with the same report structure.",
    ]
    (RUN_DIR / "WORKFLOW_EVALUATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    data = build_results()
    (RUN_DIR / "results.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(data)
    write_evaluation(data)
    print(RUN_DIR)
    print(f"rows={len(data['rows'])}")


if __name__ == "__main__":
    main()
